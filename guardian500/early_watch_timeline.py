"""Bounded multi-snapshot research batch, not continuous monitoring or trading."""
import json,subprocess,sys,time
from pathlib import Path
def main():
    out=Path(__file__).with_name("early_watch_timeline.jsonl")
    with out.open("w") as f:
        for idx in range(4):
            if idx:time.sleep(600)  # 10 minute observation spacing; ~30 min total
            proc=subprocess.run([sys.executable,str(Path(__file__).with_name("early_watch.py"))],
                                capture_output=True,text=True,timeout=180)
            event={"sample":idx+1,"ok":proc.returncode==0,"log":proc.stdout.strip()[-1500:],
                   "error":proc.stderr.strip()[-1000:]}
            f.write(json.dumps(event,ensure_ascii=False)+"\n");f.flush()
            print("EARLY_WATCH_TIMELINE="+json.dumps(event,ensure_ascii=False),flush=True)
            if proc.returncode:raise RuntimeError("Observation failed; no silent interpolation")
if __name__=="__main__":main()
