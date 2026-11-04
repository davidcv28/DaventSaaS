# Rampa automática: sube usuarios por etapas hasta que el servidor se rompe.
#
#   venv/Scripts/python.exe stress_test.py --host https://davent.com --slugs tienda-1,tienda-2
#
# "Roto" = % de fallos >= 2% o p95 >= 10s en una etapa.
#
import argparse
import csv
import os
import subprocess
import sys
import tempfile

LOCUST = [sys.executable, '-m', 'locust', '-f', 'locustfile.py', '--headless',
          '--only-summary', '--reset-stats']


def run_stage(host, slugs, users, spawn, duration):
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, DAVENT_SLUGS=slugs)
        cmd = LOCUST + ['-u', str(users), '-r', str(spawn), '-t', duration,
                        '--host', host, '--csv', os.path.join(tmp, 'r')]
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
        stats = os.path.join(tmp, 'r_stats.csv')
        if not os.path.exists(stats):
            return None, proc.stdout[-2000:] + proc.stderr[-2000:]
        rows = list(csv.DictReader(open(stats, encoding='utf-8')))
        agg = next((r for r in rows if r.get('Name') == 'Aggregated'), rows[-1])
        return {
            'requests': int(float(agg['Request Count'])),
            'failures': int(float(agg['Failure Count'])),
            'fail_pct': (int(float(agg['Failure Count'])) /
                         max(1, int(float(agg['Request Count']))) * 100),
            'rps': float(agg['Requests/s']),
            'p50': float(agg['50%']), 'p95': float(agg['95%']),
            'p99': float(agg['99%']),
        }, None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='https://www.davent.com.ar')
    p.add_argument('--slugs', default='')
    p.add_argument('--start', type=int, default=10)
    p.add_argument('--max', type=int, default=2000)
    p.add_argument('--duration', default='90s')
    p.add_argument('--fail-pct', type=float, default=2.0)
    p.add_argument('--p95-ms', type=float, default=10000)
    a = p.parse_args()

    users = a.start
    last_ok = 0
    print(f'{"users":>6} {"reqs":>7} {"fails":>6} {"fail%":>6} {"rps":>7} '
          f'{"p50":>7} {"p95":>7} {"p99":>7}')
    while users <= a.max:
        spawn = max(5, users // 5)
        res, err = run_stage(a.host, a.slugs, users, spawn, a.duration)
        if res is None:
            print(f'{users:>6}  ERROR corriendo locust\n{err}')
            break
        print(f'{users:>6} {res["requests"]:>7} {res["failures"]:>6} '
              f'{res["fail_pct"]:>5.1f}% {res["rps"]:>7.1f} '
              f'{res["p50"]:>7.0f} {res["p95"]:>7.0f} {res["p99"]:>7.0f}')
        if res['fail_pct'] >= a.fail_pct or res['p95'] >= a.p95_ms:
            print(f'\nLímite encontrado: se rompe en ~{users} usuarios '
                  f'(última etapa sana: {last_ok})')
            break
        last_ok = users
        users = min(users * 2, a.max + 1)
    else:
        print(f'\nAguantó hasta {a.max} usuarios sin romperse.')


if __name__ == '__main__':
    main()
