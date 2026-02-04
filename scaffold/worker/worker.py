#!/usr/bin/env python3
"""Simple Redis-backed worker for the scaffold.

Behavior:
- Connects to Redis using REDIS_URL env var
- BLPOP on list 'ai_jobs' and for each job runs `python -m src.main`
- By default runs in dry-run mode to avoid external API calls unless the job settings request otherwise
"""
import os
import json
import subprocess
import time
import redis

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

def main():
    print('Worker starting, connecting to Redis at', REDIS_URL)
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    while True:
        try:
            # BLPOP returns tuple (list_name, payload)
            item = r.blpop('ai_jobs', timeout=5)
            if not item:
                # no job, sleep a bit
                time.sleep(1)
                continue
            _, payload = item
            print('Received job payload:', payload)
            job = json.loads(payload)

            # Decide dry run vs real based on env or job.settings
            dry_run_env = os.getenv('DRY_RUN', 'true').lower() in ('1','true','yes')
            job_dry = job.get('settings', {}).get('dry_run', None)
            dry_run = job_dry if job_dry is not None else dry_run_env

            cmd = ['python', '-m', 'src.main']
            if dry_run:
                cmd.append('--dry-run')
            else:
                cmd.append('--no-dry-run')

            print('Running orchestrator with', cmd)
            proc = subprocess.run(cmd, capture_output=True, text=True)
            print('Orchestrator exit code:', proc.returncode)
            if proc.stdout:
                print('stdout:', proc.stdout)
            if proc.stderr:
                print('stderr:', proc.stderr)

            # Optionally push job result to a Redis list or pubsub channel for real-time UI
            try:
                result = {'job_id': job.get('id'), 'status': 'completed' if proc.returncode == 0 else 'failed', 'rc': proc.returncode}
                r.publish('ai_job_events', json.dumps(result))
            except Exception as e:
                print('Failed to publish job event:', e)

        except redis.ConnectionError as e:
            print('Redis connection error, retrying in 5s:', e)
            time.sleep(5)
        except Exception as e:
            print('Worker unexpected error:', e)
            time.sleep(2)

if __name__ == '__main__':
    main()
