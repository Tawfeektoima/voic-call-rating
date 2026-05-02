from app.worker import process_call_audio_task
import sys

call_id = int(sys.argv[1]) if len(sys.argv) > 1 else 75
print(f"Queueing task for Call ID: {call_id}")
process_call_audio_task.delay(call_id)
print("Done.")
