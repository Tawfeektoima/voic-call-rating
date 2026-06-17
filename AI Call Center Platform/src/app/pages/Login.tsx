import { useState } from 'react';
import { useNavigate } from 'react-router';
import { BadgeCheck, ChevronRight, IdCard, KeyRound, Layout, Loader2, Lock, Mail, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { useApp } from '../context/AppContext';
import { getApiBaseUrl } from '../lib/network';
import { UserRole } from '../lib/types';
import { getPermissionsForRole } from '../lib/roles';

export function Login() {
  const navigate = useNavigate();
  const { setCurrentUser, setUserRole } = useApp();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    employee_code: '',
    password: ''
  });
  const [otpChallenge, setOtpChallenge] = useState<{
    challenge_id: number;
    destination: string;
    dev_otp_code?: string;
  } | null>(null);
  const [resetChallenge, setResetChallenge] = useState<{
    challenge_id: number;
    destination: string;
    dev_otp_code?: string;
  } | null>(null);
  const [resetMode, setResetMode] = useState(false);
  const [resetData, setResetData] = useState({
    email: '',
    national_id: '',
    new_password: ''
  });
  const [otpCode, setOtpCode] = useState('');

  const getPostLoginRoute = (role: string) => {
    if (role === 'team_manager') return '/team-manager';
    if (role === 'team_leader') return '/team-leader';
    return role === 'ops_manager' ? '/notes' : '/';
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${getApiBaseUrl()}/api/auth/login`, formData);

      if (response.data.otp_required) {
        setOtpChallenge({
          challenge_id: response.data.challenge_id,
          destination: response.data.destination,
          dev_otp_code: response.data.dev_otp_code,
        });
        toast.success(`Verification code sent to ${response.data.destination}`);
        return;
      }

      const { access_token, user } = response.data;
      completeLogin(access_token, user);
    } catch (error: any) {
      console.error('Login failed:', error);
      const message = error.response?.data?.detail || 'Invalid employee code or password';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const completeLogin = (accessToken: string, user: any) => {
    const normalizedRole = user.role.toLowerCase() as UserRole;
    const normalizedUser = {
      ...user,
      role: normalizedRole,
      permissions: user.permissions?.length ? user.permissions : getPermissionsForRole(normalizedRole),
      account_status: user.account_status || user.status || 'active'
    };

    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('user', JSON.stringify(normalizedUser));

    setCurrentUser(normalizedUser);
    setUserRole(normalizedUser.role);

    toast.success(`Welcome back, ${user.name}!`);
    navigate(getPostLoginRoute(normalizedUser.role));
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpChallenge) return;
    setLoading(true);

    try {
      const response = await axios.post(`${getApiBaseUrl()}/api/auth/login/verify-otp`, {
        challenge_id: otpChallenge.challenge_id,
        otp_code: otpCode
      });
      completeLogin(response.data.access_token, response.data.user);
    } catch (error: any) {
      console.error('OTP verification failed:', error);
      const message = error.response?.data?.detail || 'Invalid or expired login code';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordResetRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${getApiBaseUrl()}/api/auth/password-reset/request`, {
        email: resetData.email,
        national_id: resetData.national_id
      });
      if (!response.data.challenge_id) {
        toast.info(response.data.message || 'If the details match, a reset code will be sent.');
        return;
      }
      setResetChallenge({
        challenge_id: response.data.challenge_id,
        destination: response.data.destination,
        dev_otp_code: response.data.dev_otp_code,
      });
      setOtpCode('');
      toast.success(`Reset code sent to ${response.data.destination}`);
    } catch (error: any) {
      console.error('Password reset request failed:', error);
      const message = error.response?.data?.detail || 'Could not start password reset';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordResetConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetChallenge) return;
    setLoading(true);

    try {
      await axios.post(`${getApiBaseUrl()}/api/auth/password-reset/confirm`, {
        challenge_id: resetChallenge.challenge_id,
        otp_code: otpCode,
        new_password: resetData.new_password
      });
      toast.success('Password reset successfully');
      setResetMode(false);
      setResetChallenge(null);
      setOtpCode('');
      setFormData({ ...formData, password: '' });
    } catch (error: any) {
      console.error('Password reset confirm failed:', error);
      const message = error.response?.data?.detail || 'Invalid or expired reset code';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const resetToLogin = () => {
    setResetMode(false);
    setResetChallenge(null);
    setOtpChallenge(null);
    setOtpCode('');
  };

  const formSubmitHandler = resetMode
    ? (resetChallenge ? handlePasswordResetConfirm : handlePasswordResetRequest)
    : (otpChallenge ? handleVerifyOtp : handleLogin);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Decorations */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute -top-24 -left-24 size-96 bg-primary/20 rounded-full blur-[100px]" />
        <div className="absolute -bottom-24 -right-24 size-96 bg-violet-500/20 rounded-full blur-[100px]" />
      </div>

      <div className="w-full max-w-md relative animate-in fade-in zoom-in duration-500">
        {/* Logo Section */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center size-16 bg-primary/10 border border-indigo-500/20 rounded-2xl mb-4 shadow-xl shadow-indigo-500/10">
            <Layout className="text-primary" size={32} />
          </div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">VoiceQA AI</h1>
          <p className="text-muted-foreground mt-2">Automated Call Intelligence Platform</p>
        </div>

        {/* Login Card */}
        <div className="bg-card/50 backdrop-blur-xl border border-border rounded-3xl p-8 shadow-2xl">
          <form onSubmit={formSubmitHandler} className="space-y-6">
            {!resetMode && !otpChallenge ? (
              <>
            <div className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">Employee Code</label>
              <div className="relative group">
                <KeyRound className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                <input 
                  type="text"
                  required
                  value={formData.employee_code}
                  onChange={e => setFormData({ ...formData, employee_code: e.target.value })}
                  placeholder="349"
                  className="w-full bg-background/50 border border-border rounded-2xl pl-12 pr-4 py-3.5 text-foreground focus:outline-none focus:border-indigo-500/50 transition-all"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between ml-1">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Password</label>
                <button
                  type="button"
                  onClick={() => {
                    setResetMode(true);
                    setOtpCode('');
                  }}
                  className="text-xs text-primary hover:text-indigo-300 font-medium"
                >
                  Forgot?
                </button>
              </div>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                <input 
                  type="password"
                  required
                  value={formData.password}
                  onChange={e => setFormData({ ...formData, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full bg-background/50 border border-border rounded-2xl pl-12 pr-4 py-3.5 text-foreground focus:outline-none focus:border-indigo-500/50 transition-all"
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={loading}
              className="w-full bg-primary hover:bg-indigo-400 disabled:bg-secondary disabled:text-muted-foreground text-white rounded-2xl py-3.5 font-bold transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 group"
            >
              {loading ? <Loader2 className="animate-spin" size={20} /> : (
                <>
                  Sign In 
                  <ChevronRight size={20} className="group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
              </>
            ) : !resetMode && otpChallenge ? (
              <>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">Verification Code</label>
                  <div className="relative group">
                    <BadgeCheck className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <input
                      type="text"
                      inputMode="numeric"
                      required
                      value={otpCode}
                      onChange={e => setOtpCode(e.target.value)}
                      placeholder="000000"
                      className="w-full bg-background/50 border border-border rounded-2xl pl-12 pr-4 py-3.5 text-foreground focus:outline-none focus:border-indigo-500/50 transition-all"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground ml-1">
                    Code sent to {otpChallenge.destination}
                    {otpChallenge.dev_otp_code ? ` - Dev code: ${otpChallenge.dev_otp_code}` : ''}
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-primary hover:bg-indigo-400 disabled:bg-secondary disabled:text-muted-foreground text-white rounded-2xl py-3.5 font-bold transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 group"
                >
                  {loading ? <Loader2 className="animate-spin" size={20} /> : (
                    <>
                      Verify Code
                      <ChevronRight size={20} className="group-hover:translate-x-1 transition-transform" />
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setOtpChallenge(null);
                    setOtpCode('');
                  }}
                  className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  Use another employee code
                </button>
              </>
            ) : resetMode && !resetChallenge ? (
              <>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">Company Email</label>
                  <div className="relative group">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <input
                      type="email"
                      required
                      value={resetData.email}
                      onChange={e => setResetData({ ...resetData, email: e.target.value })}
                      placeholder="emp-349@eiacs.com"
                      className="w-full bg-background/50 border border-border rounded-2xl pl-12 pr-4 py-3.5 text-foreground focus:outline-none focus:border-indigo-500/50 transition-all"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">National ID</label>
                  <div className="relative group">
                    <IdCard className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <input
                      type="text"
                      required
                      value={resetData.national_id}
                      onChange={e => setResetData({ ...resetData, national_id: e.target.value })}
                      placeholder="30001011234567"
                      className="w-full bg-background/50 border border-border rounded-2xl pl-12 pr-4 py-3.5 text-foreground focus:outline-none focus:border-indigo-500/50 transition-all"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-primary hover:bg-indigo-400 disabled:bg-secondary disabled:text-muted-foreground text-white rounded-2xl py-3.5 font-bold transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 group"
                >
                  {loading ? <Loader2 className="animate-spin" size={20} /> : (
                    <>
                      Send Reset Code
                      <ChevronRight size={20} className="group-hover:translate-x-1 transition-transform" />
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={resetToLogin}
                  className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  Back to sign in
                </button>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">Reset Code</label>
                  <div className="relative group">
                    <BadgeCheck className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <input
                      type="text"
                      inputMode="numeric"
                      required
                      value={otpCode}
                      onChange={e => setOtpCode(e.target.value)}
                      placeholder="000000"
                      className="w-full bg-background/50 border border-border rounded-2xl pl-12 pr-4 py-3.5 text-foreground focus:outline-none focus:border-indigo-500/50 transition-all"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground ml-1">
                    Code sent to {resetChallenge?.destination}
                    {resetChallenge?.dev_otp_code ? ` - Dev code: ${resetChallenge.dev_otp_code}` : ''}
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">New Password</label>
                  <div className="relative group">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <input
                      type="password"
                      required
                      minLength={6}
                      value={resetData.new_password}
                      onChange={e => setResetData({ ...resetData, new_password: e.target.value })}
                      placeholder="••••••••"
                      className="w-full bg-background/50 border border-border rounded-2xl pl-12 pr-4 py-3.5 text-foreground focus:outline-none focus:border-indigo-500/50 transition-all"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-primary hover:bg-indigo-400 disabled:bg-secondary disabled:text-muted-foreground text-white rounded-2xl py-3.5 font-bold transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 group"
                >
                  {loading ? <Loader2 className="animate-spin" size={20} /> : (
                    <>
                      Reset Password
                      <ChevronRight size={20} className="group-hover:translate-x-1 transition-transform" />
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={resetToLogin}
                  className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  Back to sign in
                </button>
              </>
            )}
          </form>

          <div className="mt-8 pt-8 border-t border-border text-center">
            <p className="text-muted-foreground text-sm">
              Don't have an account? <button className="text-primary font-semibold hover:text-indigo-300 transition-colors">Request Access</button>
            </p>
          </div>
        </div>

        {/* Footer Info */}
        <div className="mt-8 flex items-center justify-center gap-6 text-[10px] text-muted-foreground font-medium uppercase tracking-widest">
          <div className="flex items-center gap-1.5">
            <ShieldCheck size={12} />
            Enterprise Secure
          </div>
          <div className="flex items-center gap-1.5">
            <Layout size={12} />
            Version 1.0.0
          </div>
        </div>
      </div>
    </div>
  );
}
