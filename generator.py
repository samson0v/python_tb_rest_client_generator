# coding: utf-8
#      Copyright 2020. ThingsBoard
#  #
#      Licensed under the Apache License, Version 2.0 (the "License");
#      you may not use this file except in compliance with the License.
#      You may obtain a copy of the License at
#  #
#          http://www.apache.org/licenses/LICENSE-2.0
#  #
#      Unless required by applicable law or agreed to in writing, software
#      distributed under the License is distributed on an "AS IS" BASIS,
#      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#      See the License for the specific language governing permissions and
#      limitations under the License.
#
import re
from os import listdir
from os.path import isfile, join
import importlib
from typing import Union

from file import File
from function import Function
from generated_python_api_file import GeneratedPythonApiFile


class Generator:
    def __init__(self, path_to_ce: str, path_to_pe: str):
        self._path_to_ce = path_to_ce
        self._path_to_pe = path_to_pe
        self._pe_models_files = []
        self._ce_models_files = []
        self._pe_api_files = []
        self._ce_api_files = []
        self._clear_init_files()
        self._init_models_files()
        self._rest_client_base = GeneratedPythonApiFile(name='RestClientBase', have_init_section=True)
        self._rest_client_pe = GeneratedPythonApiFile(name='RestClientPE', have_init_section=True)
        self._rest_client_ce = GeneratedPythonApiFile(name='RestClientCE', have_init_section=False)

    @staticmethod
    def _clear_init_files():
        init_files = ['tb_rest_client/api/api_ce/__init__.py', 'tb_rest_client/api/api_pe/__init__.py',
                      'tb_rest_client/models/models_ce/__init__.py', 'tb_rest_client/models/models_pe/__init__.py']

        for file in init_files:
            with open(file, 'w') as f:
                f.write('')

    @staticmethod
    def _add_files(path: str, version: str) -> [File]:
        return tuple([File(path=path, filename=f, version=version) for f in listdir(path) if isfile(join(path, f))])

    def _init_models_files(self):
        self._pe_models_files = self._add_files(self._path_to_pe + 'swagger_client/models/', 'pe')
        self._ce_models_files = self._add_files(self._path_to_ce + 'swagger_client/models/', 'ce')
        self._ce_api_files = self._add_files(self._path_to_ce + 'swagger_client/api/', 'ce')
        self._pe_api_files = self._add_files(self._path_to_pe + 'swagger_client/api/', 'pe')

    @staticmethod
    def _write_file(path, file: File, data: [str], version: str):
        if file.filename != '__init__.py':
            with open(f'{path}{version}/' + file.filename, 'w') as f:
                f.writelines(data)

    @staticmethod
    def _read_file(path: str) -> [str]:
        with open(path, 'r') as handle_file:
            data = handle_file.readlines()

        if 'api' in path:
            data[19] = 'from tb_rest_client.api_client import ApiClient\n'

        return data

    @staticmethod
    def _import_class(abs_name: str, class_name: str) -> type:
        if class_name != 'Init':
            module = importlib.import_module(abs_name)
            return getattr(module, class_name)

    @staticmethod
    def _generate_functions(controller_name: str, method_list: Union[list, filter]) -> [Function]:
        return [Function(function_name=f.__name__, controller=controller_name,
                         params=''.join(f.__doc__.split(':param ')[2:]).split(':return')[0].replace('\n', '').split(
                             '        ')[:-1]) for f in method_list]

    @staticmethod
    def _write_init_file(file: File, module_path: str, version: str):
        # TODO: read class name from file
        with open(f'{module_path}{version}/__init__.py', 'a') as f:
            filename = file.filename.split('.')[0]
            if 'lw_m2m' in filename:
                class_name = ''.join(word.title() for word in filename[0:5].split('_')) + filename[5:6] + ''.join(
                    word.title() for word in filename[6:].split('_'))
                file.class_name = class_name
                f.write('from .' + filename + ' import ' + class_name + '\n')
            elif 'lwm_2m' in filename:
                class_name = (filename[0:1].upper() + filename[1:3] + filename[4:6]) + ''.join(
                    word.title() for word in filename[6:].split('_'))
                file.class_name = class_name
                f.write('from .' + filename + ' import ' + class_name + '\n')
            elif filename == 'url' or filename == 'uri':
                class_name = filename.upper()
                file.class_name = class_name
                f.write('from .' + filename + ' import ' + class_name + '\n')
            elif 'url' in filename:
                class_name = filename[0:3].upper() + ''.join(word.title() for word in filename[3:].split('_'))
                file.class_name = class_name
                f.write('from .' + filename + ' import ' + class_name + '\n')
            elif filename == '__init__':
                pass
            else:
                class_name = ''.join(word.title() for word in filename.split('_'))
                file.class_name = class_name
                f.write('from .' + filename + ' import ' + class_name + '\n')

    @staticmethod
    def _get_methods_without_duplicate(klass, methods: filter):
        reg = re.compile(r'\d+$')
        res = []
        duplicated_dict = {}
        for method in methods:
            match = re.search(reg, method.__name__)
            if match is None:
                res.append(method)
            else:
                duplicated_dict.update({method.__name__: match.group()})
        for duplicated_method in duplicated_dict:
            first_method_name = duplicated_method.replace(duplicated_dict[duplicated_method], '')
            for item in res:
                if item.__name__ == first_method_name:
                    res.remove(item)

        if duplicated_dict:
            print('!WARNING! The next controller has duplicates methods:')
            print('⎡' + klass.__name__)
            for i in list(duplicated_dict.keys()):
                if len(list(duplicated_dict.keys())) == list(duplicated_dict.keys()).index(i) + 1:
                    print('⎣  ' + i)
                else:
                    print('|- ' + i)

            print()
        return res

    def _generate_files(self, path: str, ce_files: [File], pe_files: [File], mode: str):
        files_set = pe_files + ce_files

        proceed_files = []

        ce_files_set = tuple([x.filename for x in ce_files])
        pe_files_set = tuple([x.filename for x in pe_files])

        for file in files_set:
            if file.filename not in proceed_files:
                if file.filename in ce_files_set and file.filename in pe_files_set:
                    handle_pe = self._read_file(
                        pe_files[pe_files_set.index(file.filename)].full_file_path)
                    handle_ce = self._read_file(
                        ce_files[ce_files_set.index(file.filename)].full_file_path)

                    if handle_ce == handle_pe:
                        self._write_file(path, file, handle_pe, 'ce')

                        if mode == 'models':
                            self._write_init_file(file, 'tb_rest_client/models/models_', 'ce')

                        if mode == 'controllers':
                            self._write_init_file(file, 'tb_rest_client/api/api_', 'ce')

                            if file.class_name:
                                klass = self._import_class('tb_rest_client.api.api_ce.' + file.filename.split('.')[0],
                                                           file.class_name)

                                method_list = filter(lambda x: x is not None, list(
                                    map(lambda x: getattr(klass, x) if callable(getattr(klass, x)) and x.startswith(
                                        '__') is False and '_with_http_info' not in x else None, dir(klass))))
                                # method_list = self._get_methods_without_duplicate(klass, method_list)

                                function_list = self._generate_functions(file.filename.split('.')[0], method_list)
                                s = ''
                                for i in function_list:
                                    s += i.str_function + '\n'
                                self._rest_client_base.methods_section = s
                                self._rest_client_base.init = klass

                    else:
                        self._write_file(path, file, handle_ce, 'ce')
                        self._write_file(path, file, handle_pe, 'pe')

                        if mode == 'models':
                            self._write_init_file(file, 'tb_rest_client/models/models_', 'ce')
                            self._write_init_file(file, 'tb_rest_client/models/models_', 'pe')

                        if mode == 'controllers':
                            self._write_init_file(file, 'tb_rest_client/api/api_', 'ce')
                            self._write_init_file(file, 'tb_rest_client/api/api_', 'pe')

                            if file.class_name:
                                ce_file = ce_files[ce_files_set.index(file.filename)]
                                pe_file = pe_files[pe_files_set.index(file.filename)]

                                # TODO: remake writing init file strategy
                                self._write_init_file(ce_file, 'tb_rest_client/api/api_', 'ce')
                                self._write_init_file(pe_file, 'tb_rest_client/api/api_', 'pe')

                                pe_klass = self._import_class(
                                    f'tb_rest_client.api.api_pe.' + pe_file.filename.split('.')[0], pe_file.class_name)
                                ce_klass = self._import_class(
                                    f'tb_rest_client.api.api_ce.' + ce_file.filename.split('.')[0], ce_file.class_name)

                                pe_method_list = filter(lambda x: x is not None, list(
                                    map(lambda x: getattr(pe_klass, x) if callable(
                                        getattr(pe_klass, x)) and x.startswith(
                                        '__') is False and '_with_http_info' not in x else None, dir(pe_klass))))
                                # pe_method_list = self._get_methods_without_duplicate(pe_klass, pe_method_list)

                                pe_function_list = self._generate_functions(pe_file.filename.split('.')[0],
                                                                            pe_method_list)
                                pe_function_names_dict = {func.name: func for func in pe_function_list}

                                ce_method_list = filter(lambda x: x is not None, list(
                                    map(lambda x: getattr(ce_klass, x) if callable(
                                        getattr(ce_klass, x)) and x.startswith(
                                        '__') is False and '_with_http_info' not in x else None, dir(ce_klass))))
                                # ce_method_list = self._get_methods_without_duplicate(ce_klass, ce_method_list)
                                ce_function_list = self._generate_functions(ce_file.filename.split('.')[0],
                                                                            ce_method_list)
                                ce_function_names_dict = {func.name: func for func in ce_function_list}

                                the_same_functions_by_name = set(ce_function_names_dict.keys()) & set(pe_function_names_dict.keys())
                                with_the_same_params = [func[0] for func in list(
                                    filter(lambda x: x[0].params == x[1].params,
                                           [(ce_function_names_dict[function_name],
                                             pe_function_names_dict[function_name])
                                            for function_name in the_same_functions_by_name]))]
                                not_the_same_function = []
                                for func in set(list(ce_function_names_dict.keys()) + list(pe_function_names_dict.keys())):
                                    if func in ce_function_names_dict and func not in pe_function_names_dict or \
                                        (func in the_same_functions_by_name and ce_function_names_dict[func] not in with_the_same_params and ce_function_names_dict[func] not in not_the_same_function):
                                        not_the_same_function.append(ce_function_names_dict[func])
                                    elif func in pe_function_names_dict and func not in ce_function_names_dict or \
                                            (func in the_same_functions_by_name and func not in with_the_same_params):
                                        not_the_same_function.append(pe_function_names_dict[func])

                                try:
                                    for i in with_the_same_params:
                                        self._rest_client_base.methods_section = i.str_function + '\n'

                                    for i in not_the_same_function:
                                        if ce_function_names_dict.get(i.name):
                                            self._rest_client_ce.methods_section = ce_function_names_dict[
                                                                                       i.name].str_function + '\n'
                                            self._rest_client_base.init = ce_klass
                                        if pe_function_names_dict.get(i.name):
                                            self._rest_client_pe.methods_section = pe_function_names_dict[
                                                                                       i.name].str_function + '\n'
                                            self._rest_client_pe.init = pe_klass
                                except Exception as e:
                                    print(e)
                else:
                    handle_data = self._read_file(file.full_file_path)
                    self._write_file(path, file, handle_data, file.version)

                    if mode == 'models':
                        self._write_init_file(file, 'tb_rest_client/models/models_', file.version)

                    if mode == 'controllers':
                        self._write_init_file(file, 'tb_rest_client/api/api_', file.version)

                        klass = self._import_class(
                            f'tb_rest_client.api.api_{file.version}.' + file.filename.split('.')[0],
                            ''.join(word.title() for word in file.filename.split('_')).split('.')[0])
                        method_list = filter(lambda x: x is not None, list(
                            map(lambda x: getattr(klass, x) if callable(getattr(klass, x)) and x.startswith(
                                '__') is False and '_with_http_info' not in x else None, dir(klass))))
                        # method_list = self._get_methods_without_duplicate(klass, method_list)

                        function_list = self._generate_functions(file.filename.split('.')[0], method_list)

                        s = ''
                        for i in function_list:
                            s += i.str_function + '\n'

                        if file.version == 'ce':
                            self._rest_client_ce.methods_section = s
                            self._rest_client_base.init = klass
                        else:
                            self._rest_client_pe.methods_section = s
                            self._rest_client_pe.init = klass

                proceed_files.append(file.filename)

        with open('tb_rest_client/rest_client_base.py', 'w') as f:
            f.writelines(self._rest_client_base.generate_file())

        with open('tb_rest_client/rest_client_pe.py', 'w') as f:
            f.writelines(self._rest_client_pe.generate_file())

        with open('tb_rest_client/rest_client_ce.py', 'w') as f:
            f.writelines(self._rest_client_ce.generate_file())

    def generate(self):
        self._generate_files('tb_rest_client/models/models_', self._ce_models_files, self._pe_models_files, 'models')
        self._generate_files('tb_rest_client/api/api_', self._ce_api_files, self._pe_api_files, 'controllers')
