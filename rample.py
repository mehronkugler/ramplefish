""" Run presets in Rally, given a config file """
import json
import concurrent.futures
import pprint
import sys

from adapters.adapter import RallyClient
from runners.individual import RallyTest

__author__ = "Mehron Kugler"
__license__ = "GNU GPLv3"
__email__ = "mkugler@member.fsf.org"
__status__ = "Prototype"

pp = pprint.PrettyPrinter(indent=4)

"""
max_workers=2 with 3 tests: runtime 23 sec
max_workers=5 with 3 tests: runtime 13 sec
"""


def run_test(test_dict, config, rc):
    if not test_dict.get('enabled', False):
        print('Skipping {}, not enabled'.format(test_dict.get('name')))
        return 1
    asset = test_dict.get('asset') or config.get('default_test_asset')
    combination = 'PRESET: \'{}\' ASSET: \'{}\''.format(
        test_dict.get('name'),
        asset
    )
    print('START: {}'.format(combination))
    single_runner = RallyTest(
        test_dict.get('name'), asset, test_dict.get('dynamicPresetData')
    )
    # Blocking wait (up to 1 min)
    single_runner.run(rc)
    if not single_runner.test_completed:
        preset_failures.append(
            {
                'name': test_dict.get('name'),
                'asset': asset,
                'error': single_runner.error_msg,
                'trace': single_runner.error_trace_uri
            }
        )


def main():
    config_file_json = 'sample_instance_config.json'
    if len(sys.argv) > 1:
        config_file_json = sys.argv[1]
    with open(config_file_json, 'r') as config_file:
        config_data = config_file.read()

    config = json.loads(config_data)
    print("RampleFish: Running config using {}".format(config_file_json))
    print('Rally instance: {}\n'.format(config.get('env_hostname')))
    rc = RallyClient(config.get('env_hostname'), config.get('api_key'))

    preset_failures = []

    """ Presets """
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Start the load operations and mark each future with the test
        future_to_test = {
            executor.submit(run_test, test, config, rc): test for test in config.get('tests')
        }
        for future in concurrent.futures.as_completed(future_to_test):
            test = future_to_test[future]
            try:
                data = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (test, exc))
            else:
                # print('Test completed: {}'.format(test['name']))
                print('.', end="", flush=True)
        print("\n")

    # Tally presets
    presets_passed = len(config.get('tests')) - len(preset_failures)
    print('\nPresets: {} passed, {} total'.format(presets_passed, len(config.get('tests'))))

    if preset_failures:
        print('Summary of preset failures:')
        for failure in preset_failures:
            pp.pprint(failure)

    if preset_failures:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
