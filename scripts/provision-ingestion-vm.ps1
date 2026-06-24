param(
    [string]$VmName = "call-rating-ingestion",
    [string]$SwitchName = "CallRatingIngestionNAT",
    [string]$NatName = "CallRatingIngestionNAT",
    [string]$InternalPrefix = "10.42.0.0/24",
    [string]$HostIpAddress = "10.42.0.1",
    [int]$ProcessorCount = 4,
    [UInt64]$MemoryStartupBytes = 8GB,
    [UInt64]$VhdSizeBytes = 80GB,
    [string]$VhdxPath = (Join-Path $PSScriptRoot "..\vm\ingestion\call-rating-ingestion.vhdx")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-FallbackInstructions {
    Write-Host ""
    Write-Host "Hyper-V is not available on this host."
    Write-Host ""
    Write-Host "Use the documented VirtualBox fallback instead:"
    Write-Host "  1. Install VirtualBox on the Windows host."
    Write-Host "  2. Create an Ubuntu Server LTS VM with the same CPU, RAM, and disk sizing."
    Write-Host "  3. Use NAT networking only."
    Write-Host "  4. Disable shared folders, clipboard sharing, drag-and-drop, USB passthrough, and host-drive mounts."
    Write-Host "  5. Keep the VM disk on a BitLocker-protected Windows volume and enable Ubuntu disk encryption during install."
    Write-Host "  6. Keep raw recordings only inside the guest."
    Write-Host ""
}

function Test-Administrator {
    $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-HyperVAvailable {
    if ($env:OS -ne "Windows_NT") {
        return $false
    }

    $requiredCommands = @(
        "Get-VM",
        "New-VM",
        "New-VMSwitch",
        "Set-VMProcessor",
        "Set-VMFirmware",
        "Get-NetNat",
        "New-NetNat",
        "Get-NetIPAddress",
        "New-NetIPAddress"
    )

    foreach ($commandName in $requiredCommands) {
        if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
            return $false
        }
    }

    return $true
}

function Assert-BitLockerProtectedPath {
    param(
        [string]$Path
    )

    $driveRoot = [System.IO.Path]::GetPathRoot([System.IO.Path]::GetFullPath($Path)).TrimEnd('\')
    if (-not $driveRoot) {
        throw "Could not resolve the drive for VHDX path '$Path'."
    }

    if (-not (Get-Command Get-BitLockerVolume -ErrorAction SilentlyContinue)) {
        throw "BitLocker management tools are unavailable. Store the VHDX on a BitLocker-protected drive and rerun from a Windows host with BitLocker tools installed."
    }

    $volume = Get-BitLockerVolume -MountPoint $driveRoot
    if (-not $volume) {
        throw "Could not inspect BitLocker status for drive '$driveRoot'."
    }

    if ($volume.ProtectionStatus.ToString() -ne "On" -or $volume.VolumeStatus.ToString() -ne "FullyEncrypted") {
        throw "VHDX path '$Path' must be stored on a fully encrypted BitLocker volume. Current drive '$driveRoot' status: protection=$($volume.ProtectionStatus), volume=$($volume.VolumeStatus)."
    }
}

function Ensure-InternalSwitch {
    param(
        [string]$Name,
        [string]$HostAddress,
        [string]$Prefix,
        [string]$Nat
    )

    $existingSwitch = Get-VMSwitch -Name $Name -ErrorAction SilentlyContinue
    if (-not $existingSwitch) {
        Write-Host "Creating internal Hyper-V switch '$Name'..."
        New-VMSwitch -Name $Name -SwitchType Internal | Out-Null
    }

    $adapterName = "vEthernet ($Name)"
    $existingAddress = Get-NetIPAddress -InterfaceAlias $adapterName -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -eq $HostAddress }
    if (-not $existingAddress) {
        $staleAddresses = Get-NetIPAddress -InterfaceAlias $adapterName -AddressFamily IPv4 -ErrorAction SilentlyContinue
        foreach ($staleAddress in $staleAddresses) {
            Remove-NetIPAddress -InterfaceAlias $adapterName -IPAddress $staleAddress.IPAddress -Confirm:$false -ErrorAction SilentlyContinue
        }

        Write-Host "Assigning host-side NAT address $HostAddress to '$adapterName'..."
        New-NetIPAddress -InterfaceAlias $adapterName -IPAddress $HostAddress -PrefixLength 24 | Out-Null
    }

    $existingNat = Get-NetNat -Name $Nat -ErrorAction SilentlyContinue
    if (-not $existingNat) {
        Write-Host "Creating NAT network '$Nat' for prefix $Prefix..."
        New-NetNat -Name $Nat -InternalIPInterfaceAddressPrefix $Prefix | Out-Null
    }
}

function Ensure-VM {
    param(
        [string]$Name,
        [string]$Switch,
        [string]$DiskPath,
        [UInt64]$DiskSize,
        [UInt64]$MemoryBytes,
        [int]$CpuCount
    )

    $diskDir = Split-Path -Parent $DiskPath
    New-Item -ItemType Directory -Force -Path $diskDir | Out-Null

    if (-not (Test-Path $DiskPath)) {
        Write-Host "Creating VHDX at $DiskPath..."
        New-VHD -Path $DiskPath -Dynamic -SizeBytes $DiskSize | Out-Null
    }

    $existingVm = Get-VM -Name $Name -ErrorAction SilentlyContinue
    if (-not $existingVm) {
        Write-Host "Creating Generation 2 VM '$Name'..."
        New-VM -Name $Name -Generation 2 -MemoryStartupBytes $MemoryBytes -VHDPath $DiskPath -SwitchName $Switch | Out-Null
    }

    Set-VMProcessor -VMName $Name -Count $CpuCount
    Set-VMMemory -VMName $Name -DynamicMemoryEnabled $false -StartupBytes $MemoryBytes
    Set-VMFirmware -VMName $Name -EnableSecureBoot On -SecureBootTemplate "MicrosoftUEFICertificateAuthority"

    $vm = Get-VM -Name $Name
    if ($vm.State -ne "Off") {
        Write-Warning "VM '$Name' is currently $($vm.State). This helper does not start or stop it."
    }
}

if (-not (Test-Administrator)) {
    Write-Host "Run this script from an elevated PowerShell session."
    Write-Host "It needs admin rights to create the Hyper-V switch, NAT, and VM."
    Write-FallbackInstructions
    exit 2
}

if (-not (Test-HyperVAvailable)) {
    Write-FallbackInstructions
    exit 3
}

try {
    Assert-BitLockerProtectedPath -Path $VhdxPath
    Ensure-InternalSwitch -Name $SwitchName -HostAddress $HostIpAddress -Prefix $InternalPrefix -Nat $NatName
    Ensure-VM -Name $VmName -Switch $SwitchName -DiskPath $VhdxPath -DiskSize $VhdSizeBytes -MemoryBytes $MemoryStartupBytes -CpuCount $ProcessorCount

    Write-Host ""
    Write-Host "Provisioning complete."
    Write-Host "VM name: $VmName"
    Write-Host "CPU count: $ProcessorCount"
    Write-Host "Memory: $([math]::Round($MemoryStartupBytes / 1GB, 2)) GB"
    Write-Host "VHDX: $VhdxPath"
    Write-Host "Switch: $SwitchName"
    Write-Host "NAT: $NatName ($InternalPrefix)"
    Write-Host ""
    Write-Host "The VM was created or updated, but it was not started."
    Write-Host "Next step: install Ubuntu Server LTS inside the guest with LUKS-enabled storage and run the guest bootstrap script."
}
catch {
    Write-Host ""
    Write-Error "Failed to provision the Hyper-V VM: $($_.Exception.Message)"
    Write-FallbackInstructions
    exit 1
}
