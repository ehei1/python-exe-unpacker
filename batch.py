'''
it add magic number and decompile with unpacked files

reference:
https://item4.blog/2018-11-04/Extract-Python-Code-from-PyInstaller-EXE-File/#fn-1
'''
import argparse
import os.path
import pkgutil
import shutil
import subprocess
import sys
import time


def main(in_path, intermediate_path, out_path, magic_number) -> None:
    cwd = os.getcwd()
    in_path = os.path.join(cwd, in_path)
    py_ext = 'py'

    if os.path.exists(out_path):
        shutil.rmtree(out_path)

    os.mkdir(out_path)

    if not os.path.exists(intermediate_path):
        os.mkdir(intermediate_path)

    script_path = os.path.split(sys.executable)[0]
    decompyle3_path = os.path.join(script_path, 'decompyle3.exe')
    unpyc_path = os.path.join(cwd, 'unpyc37', 'unpyc3.py')
    decompile_failed_files = []
    error_string = b'Deparsing stopped due to parse error\r\n'
    error_string_len = len(error_string)
    module_names = set(v[1] for v in pkgutil.iter_modules())
    module_names.update(sys.builtin_module_names)

    for file_name in os.listdir(in_path):
        print('{}...'.format(file_name), end='')
        start_time = time.time()
        module_name = file_name.split('.')[0]

        if module_name in module_names:
            print('module')
            continue

        pyc_file_path = os.path.join(in_path, file_name)

        with open(pyc_file_path, 'rb') as pyc_file:
            bytes = pyc_file.read()

        inter_file_path = os.path.join(intermediate_path, file_name)

        if not os.path.exists(inter_file_path):
            with open(inter_file_path, 'wb') as inter_file:
                data = list(bytes)
                data[7:11] = magic_number
                bytes = bytearray(data)

                inter_file.write(bytes)

        try:
            print('decompyle3...', end='')
            result = subprocess.check_output((decompyle3_path, inter_file_path), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            error = True
        else:
            error = False

        if error or result[-error_string_len:] == error_string:
            try:
                print('unpyc37...', end='')

                # it lacks with some file
                result = subprocess.check_output((sys.executable, unpyc_path, inter_file_path), timeout=5)
                error = False
                print('{:.2f}'.format(elapsed_time), end='')
            except subprocess.TimeoutExpired:
                decompile_failed_files.append(file_name)
                error = True
            except subprocess.CalledProcessError:
                decompile_failed_files.append(file_name)
                error = True
            except Exception as e:
                print(e, end='')

        elapsed_time = time.time() - start_time
        error_sign = 'x' if error else ''
        print('{:.2f}s...{}'.format(elapsed_time, error_sign))

        if not error:
            py_file_name = os.path.splitext(file_name)[0]
            py_file_path = os.path.join(out_path, py_file_name + '.' + py_ext)

            with open(py_file_path, 'wb') as py_file:
                py_file.write(result)

    print('')

    if decompile_failed_files:
        decompile_failed_files = tuple('\t{}'.format(v) for v in decompile_failed_files)
        decompile_failed_files = '\n'.join(decompile_failed_files)

        print('decompile failed\n{}'.format(decompile_failed_files))

    print('done')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="The program will add magic number and decompile to py")
    parser.add_argument("-i", dest="in_path", help="relative directory which pyc locate", required=True)
    parser.add_argument("-r", dest="intermediate_path", help="relative directory which intermediate pyc'll locate", default="pyc")
    parser.add_argument("-o", dest="out_path", help="relative directory which py locate", default="py")
    # I can't find magic number automatically
    parser.add_argument("--magic_number", "-m", dest="magic_number", default="0x7079,0x6930,0x0101,0x0000")
    args = parser.parse_args()
    magic_number = []

    for value in args.magic_number.split(','):
        value = int(value, base=16)

        for v in (value >> 8, value):
            v &= 0xff
            magic_number.append(v)

    main(args.in_path, args.intermediate_path, args.out_path, magic_number)