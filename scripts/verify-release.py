"""Run supported release checks in isolated Qt processes, with per-module logs."""
from pathlib import Path
import subprocess,sys,os,json,re
ROOT=Path(__file__).resolve().parents[1]
MODULES='app_controller app_state auto_usage_sync branding chain classifier cli codex_loop_extension diagnostics display_preferences localization_coverage history pause local_multi_schedule local_save_feedback local_self_test local_warmup_recovery provider_runtime providers protocol quota reliability schedule scheduled_only startup single_instance state_resilience trigger update_ui updates'.split()
def main():
 out=ROOT/'artifacts'/'release-checks';out.mkdir(parents=True,exist_ok=True)
 env=dict(os.environ,QT_QPA_PLATFORM='offscreen',PYTHONUTF8='1')
 env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+str(ROOT/'tests')
 rows=[]
 for name in MODULES:
  try:
   r=subprocess.run([sys.executable,'-X','utf8','-m','unittest','discover','-s',str(ROOT/'tests'),'-p',f'test_{name}.py'],cwd=ROOT,env=env,text=True,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=75)
   output=r.stdout;code=r.returncode
  except subprocess.TimeoutExpired as exc:output=str(exc);code=124
  (out/f'test_{name}.log').write_text(output,encoding='utf-8')
  match=re.search(r'Ran (\d+) tests?',output)
  row={'module':name,'exit_code':code,'tests':int(match[1]) if match else 0};rows.append(row)
  print(('PASS' if code==0 else 'FAIL')+f' {name}: {row["tests"]} tests',flush=True)
 (out/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
 print(f'Total: {sum(r["tests"] for r in rows)} tests; failed modules: {sum(r["exit_code"]!=0 for r in rows)}',flush=True)
 return int(any(row['exit_code'] for row in rows))
if __name__=='__main__':raise SystemExit(main())
