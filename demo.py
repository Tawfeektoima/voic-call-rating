import gradio as gr
import requests
import time
import os

API_BASE_URL = "http://localhost:8000/api"

def ensure_setup():
    """Create a dummy employee and campaign if they don't exist."""
    try:
        emps = requests.get(f"{API_BASE_URL}/admin/employees").json()
        if not emps:
            requests.post(f"{API_BASE_URL}/admin/employees", json={
                "name": "Demo Agent",
                "employee_code": "DEMO-001"
            })
            
        camps = requests.get(f"{API_BASE_URL}/admin/campaigns").json()
        if not camps:
            requests.post(f"{API_BASE_URL}/admin/campaigns", json={
                "name": "Citizens Debt Relief QA",
                "evaluation_prompt": "Evaluate based on strict Citizens Debt Relief rules: Opening & Verification, Hold Etiquette, Empathy, Practical Solutions, Jargon, and Professional Closing."
            })
    except Exception as e:
        print(f"Failed to setup demo data: {e}")

def get_demo_ids():
    try:
        emps = requests.get(f"{API_BASE_URL}/admin/employees").json()
        camps = requests.get(f"{API_BASE_URL}/admin/campaigns").json()
        if not emps or not camps:
            return None, None
        return emps[0]['id'], camps[0]['id']
    except Exception as e:
        print(f"Error connecting to backend: {e}")
        return None, None

def process_single_audio(audio_path):
    if not audio_path:
        return "No audio file provided.", "N/A"
        
    ensure_setup()
    emp_id, camp_id = get_demo_ids()
    if not emp_id or not camp_id:
        return "System setup incomplete.", "N/A"
        
    # Upload Audio
    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
        data = {"employee_id": emp_id, "campaign_id": camp_id}
        res = requests.post(f"{API_BASE_URL}/audio/upload", files=files, data=data)
        if res.status_code != 200:
            return f"Upload failed: {res.text}", "N/A"
        call_id = res.json()["call_id"]
        
    yield f"Processing... (Call ID: {call_id})", "Processing..."
    
    status = "pending"
    while status not in ["evaluated", "failed"]:
        time.sleep(3)
        res = requests.get(f"{API_BASE_URL}/audio/{call_id}").json()
        status = res.get("status", "failed")
        if status == "failed":
            yield f"Error: {res.get('error_message')}", "Failed"
            return
        yield f"Status: {status.upper()}", "Processing..."

    final_text = f"## Transcript\n\n{res.get('transcript')}\n\n"
    
    final_text += "## ✅ Strengths\n"
    for s in res.get("strengths", []):
        final_text += f"- {s}\n"
    if not res.get("strengths"):
        final_text += "- None identified.\n"

    final_text += "\n## ⚠️ Weaknesses\n"
    for w in res.get("weaknesses", []):
        # We use .get('issue') because we renamed the field
        issue_name = w.get('issue') or w.get('category', 'General')
        final_text += f"- **{issue_name}** (-{w['deduction']} pts): {w['detail']}\n"
    if not res.get("weaknesses"):
        final_text += "- None identified.\n"
        
    score_display = f"{res.get('evaluation_score', 'N/A')} / 100"
    yield final_text, score_display

def process_batch_audio(audio_files):
    if not audio_files:
        yield [], "No files provided."
        return
        
    ensure_setup()
    emp_id, camp_id = get_demo_ids()
    if not emp_id or not camp_id:
        yield [], "❌ System setup incomplete. Please make sure the backend (port 8000) is running."
        return

    results = []
    total_score = 0
    successful_calls = 0
    total_audio_duration = 0
    batch_start_time = time.time()

    yield results, "Starting batch process..."

    for i, file_obj in enumerate(audio_files):
        # file_obj in Gradio represents a file path
        filepath = file_obj
        filename = os.path.basename(filepath)
        
        # Add placeholder row: Filename, Status, Audio Length, Process Time, Score
        results.append([filename, "Processing...", "N/A", "N/A", "N/A"])
        yield results, f"Processing file {i+1} of {len(audio_files)}..."
        
        start_time = time.time()
        
        try:
            # Upload
            with open(filepath, "rb") as f:
                files = {"file": (filename, f, "audio/wav")}
                data = {"employee_id": emp_id, "campaign_id": camp_id}
                res = requests.post(f"{API_BASE_URL}/audio/upload", files=files, data=data)
            
            if res.status_code != 200:
                results[-1][1] = "Upload Failed"
                continue
                
            call_id = res.json()["call_id"]
            
            # Poll
            status = "pending"
            while status not in ["evaluated", "failed"]:
                time.sleep(2)
                call_res = requests.get(f"{API_BASE_URL}/audio/{call_id}").json()
                status = call_res.get("status", "failed")
                
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            
            if status == "evaluated":
                score = call_res.get("evaluation_score", 0)
                audio_len = call_res.get("audio_duration", 0)
                total_score += score
                total_audio_duration += audio_len
                successful_calls += 1
                
                # Format durations
                audio_len_str = f"{int(audio_len // 60)}m {int(audio_len % 60)}s"
                results[-1] = [filename, "Evaluated", audio_len_str, f"{duration}s", str(score)]
            else:
                results[-1] = [filename, "Failed", "N/A", f"{duration}s", "N/A"]
                
        except Exception as e:
            results[-1][1] = f"Error: {str(e)}"
            
        # Yield update after each file
        yield results, f"Processing file {i+1} of {len(audio_files)}..."

    # Final summary
    total_batch_duration = round(time.time() - batch_start_time, 2)
    total_audio_min = int(total_audio_duration // 60)
    total_audio_sec = int(total_audio_duration % 60)
    
    if successful_calls > 0:
        avg_score = round(total_score / successful_calls, 2)
        summary = f"""### **✅ Batch Complete!**
- **Total Files**: {len(audio_files)}
- **Successful**: {successful_calls}
- **Average Score**: {avg_score} / 100
- **Total Audio Processed**: {total_audio_min}m {total_audio_sec}s
- **Total Time Taken**: {int(total_batch_duration // 60)}m {int(total_batch_duration % 60)}s
"""
    else:
        summary = "### **Batch Complete!**\n\nNo successful evaluations."
        
    yield results, summary

def launch_ui():
    with gr.Blocks(title="Call Rating Platform UI") as demo:
        gr.Markdown("# 🎙️ Call Rating Platform")
        
        with gr.Tabs():
            with gr.TabItem("Single Call Analysis"):
                with gr.Row():
                    with gr.Column():
                        audio_input = gr.Audio(type="filepath", label="Upload Recording")
                        analyze_btn = gr.Button("🚀 Upload & Analyze", variant="primary")
                    with gr.Column():
                        score_output = gr.Textbox(label="AI Evaluation Score")
                transcript_output = gr.Markdown(label="Results")
                analyze_btn.click(fn=process_single_audio, inputs=audio_input, outputs=[transcript_output, score_output])

            with gr.TabItem("Batch Processing"):
                gr.Markdown("Select multiple audio files. They will be processed **one by one** to monitor time and score safely without overloading the GPU.")
                with gr.Row():
                    with gr.Column(scale=1):
                        batch_audio_input = gr.File(file_count="multiple", file_types=["audio"], label="Select Audio Files")
                        batch_analyze_btn = gr.Button("🚀 Start Batch Process", variant="primary")
                    with gr.Column(scale=2):
                        batch_summary_output = gr.Markdown(label="Summary")
                
                batch_results_table = gr.Dataframe(headers=["Filename", "Status", "Audio Length", "Process Time", "Score"], label="Batch Results", interactive=False)
                
                batch_analyze_btn.click(
                    fn=process_batch_audio,
                    inputs=batch_audio_input,
                    outputs=[batch_results_table, batch_summary_output]
                )

    demo.launch(server_port=7860, share=True, inbrowser=True)

if __name__ == "__main__":
    print("[*] Starting UI... please wait.")
    launch_ui()
