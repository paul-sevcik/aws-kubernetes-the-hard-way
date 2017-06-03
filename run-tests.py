
import re
import subprocess

import stack

if __name__ == '__main__':
    instances = stack.instances()
    regex = re.compile('Count: (\d+), Failed: (\d+), Skipped: (\d+)')
    count_tot = 0
    failed_tot = 0
    skipped_tot = 0
    cmd_template = 'python stack.py ssh {} "sudo /usr/local/bin/goss -g /usr/local/etc/goss.yaml validate" 2>&1'
    for instance in instances:
        print('-' * 20)
        print('{}:'.format(instance))
        result = subprocess.run(
            cmd_template.format(instance),
            shell=True,
            stdout=subprocess.PIPE,
        )
        for line in result.stdout.decode('UTF-8').split('\n'):
            if line.startswith('Warning: Permanently added'):
                continue
            print(line)
            matches = regex.match(line)
            if matches:
                count_tot += int(matches.group(1))
                failed_tot += int(matches.group(2))
                skipped_tot += int(matches.group(3))

    print()
    print('-'*20)
    print('Summary:')
    print('    Count: {}'.format(count_tot))
    print('    Failed: {}'.format(failed_tot))
    print('    Skipped: {}'.format(skipped_tot))
    print('-'*20)

    if failed_tot > 0:
        import sys
        sys.exit(1)
