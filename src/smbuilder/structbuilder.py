import util

import os


def get_default_value(type):
    if type == 'float':
        return  '0.0'
    elif type == 'Handle':
        return  'INVALID_HANDLE'
    else:
        return '0'


class StructMember:
    def __init__(this, structname, name, type, is_array=False, array_size=1):
        this.name = name
        this.type = type
        this.is_array = is_array
        this.array_size = array_size

        if array_size <= 0:
            msg = 'Illegal array size for {}.{}'.format(structname, name)
            raise ValueError(msg)

        # some function/variable names to use for this struct eleement
        this.function_suffix = name[0].upper()
        for letter in name[1:]:
            this.function_suffix += letter

        this.setter_function_name = '{}_Set{}'.format(structname, this.function_suffix)
        this.getter_function_name = '{}_Get{}'.format(structname, this.function_suffix)
        this.setter_method_name = 'Set{}'.format(this.function_suffix)
        this.getter_method_name = 'Get{}'.format(this.function_suffix)

    @staticmethod
    def from_keyvalue(structname, name, fieldtype):
        is_array = False
        array_size = 1

        array_index_start = fieldtype.find('[')
        array_index_end = fieldtype.find(']')

        if array_index_start == -1 and array_index_end == -1:
            type = fieldtype
            is_array = False
            array_size = 1
            # not an array
        elif array_index_start == -1 and array_index_end != -1:
            raise SyntaxError('No array opening token for {}.{}'.format(structname, name))
        elif array_index_start != -1 and array_index_end == -1:
            raise SyntaxError('No array closing token for {}.{}'.format(structname, name))
        else:
            # is an array
            is_array = True
            substr = fieldtype[array_index_start + 1:array_index_end]
            array_size = int(substr)
            type = fieldtype[:array_index_start]

        return StructMember(structname, name, type, is_array, array_size)



def create_struct_functions(name, elems):
    lines = []

    function_prefix = name
    struct_param_name = name.lower() + '_'

    constructor_name = '{}_New'.format(name)

    # helper macros
    lines.append('#define Create{}() {}:{}()'.format(name, name, constructor_name))
    lines.append('#define {}FromArray(%1,%2) ({}:GetArrayCell(%1, %2))'.format(name, name))
    lines.append('')

    # constructor
    lines.append('stock Handle {}() {{'.format(constructor_name))
    lines.append('\tHandle dataList = CreateArray();')

    curr_index = 0
    for e in elems:
        default_value = get_default_value(e.type)
        if e.is_array:
            lines.append('\tfor(int i = 0; i < {}; i++)'.format(e.array_size))
            lines.append('\t\tPushArrayCell(dataList, {});'.format(default_value))
        else:
            lines.append('\tPushArrayCell(dataList, {});'.format(default_value))

        curr_index += e.array_size

    lines.append('\treturn dataList;')
    lines.append('}')
    lines.append('')


    # getters
    curr_index = 0
    for e in elems:
        elem_func_suffix = e.name.title()

        if e.is_array:
            lines.append('stock void {}_Get{}(Handle {}, {} buffer[{}]) {{'.format(function_prefix, elem_func_suffix, struct_param_name, e.type, e.array_size))
            lines.append('\tfor (int i = 0; i < {}; i++)'.format(e.array_size))
            lines.append('\t\tbuffer[i] = GetArrayCell({}, i + {});'.format(struct_param_name, curr_index))
            lines.append('}')

        else:
            lines.append('stock {} {}_Get{}(Handle {}) {{'.format(e.type, function_prefix, elem_func_suffix, struct_param_name))
            lines.append('\treturn GetArrayCell({}, {});'.format(struct_param_name, curr_index))
            lines.append('}')

        lines.append('')
        curr_index += e.array_size


    # setters
    curr_index = 0
    for e in elems:
        elem_func_suffix = e.name.title()

        if e.is_array:
            lines.append('stock void {}_Set{}(Handle {}, const {} value[{}]) {{'.format(function_prefix, elem_func_suffix, struct_param_name, e.type, e.array_size))
            lines.append('\tfor (int i = 0; i < {}; i++)'.format(e.array_size))
            lines.append('\t\tSetArrayCell({}, i + {}, value[i]);'.format(struct_param_name, curr_index))
            lines.append('}')

        else:
            lines.append('stock void {}_Set{}(Handle {}, {} value) {{'.format(function_prefix, elem_func_suffix, struct_param_name, e.type))
            lines.append('\tSetArrayCell({}, {}, value);'.format(struct_param_name, curr_index))
            lines.append('}')

        lines.append('')
        curr_index += e.array_size

    # method map
    lines.append('methodmap {} < Handle {{'.format(name))

    for e in elems:
        # getter
        if e.is_array:
            # getter
            lines.append('\tpublic void {}({} buffer[{}]) {{'.format(e.getter_method_name, e.type, e.array_size))
            lines.append('\t\t{}(this, buffer);'.format(e.getter_function_name))
            lines.append('\t}')
            lines.append('')

            # setter
            lines.append('\tpublic void {}(const {} value[{}]) {{'.format(e.setter_method_name, e.type, e.array_size))
            lines.append('\t\t{}(this, value);'.format(e.setter_function_name))
            lines.append('\t}')
            lines.append('')

        else:
            # getter
            lines.append('\tpublic {} {}() {{'.format(e.type, e.getter_method_name))
            lines.append('\t\treturn {}(this);'.format(e.getter_function_name))
            lines.append('\t}')
            lines.append('')

            # setter
            lines.append('\tpublic void {}({} x_) {{'.format(e.setter_method_name, e.type))
            lines.append('\t\t{}(this, x_);'.format(e.setter_function_name))
            lines.append('\t}')
            lines.append('')

            # for non-arrays, we also create properties
            lines.append('\tproperty {} {} {{'.format(e.type, e.name))
            lines.append('\t\tpublic set() = {};'.format(e.setter_function_name))
            lines.append('\t\tpublic get() = {};'.format(e.getter_function_name))
            lines.append('\t}')
            lines.append('')


    lines.append('}')
    lines.append('')

    lines = map(lambda l: l.replace('\t', '    '), lines)

    text = '\n'.join(lines)

    return text


Structs = {}
def add_struct(name, fields):
    global Structs
    values = []
    for member_name in fields:
        member_type = fields[member_name]
        values.append((member_name, member_type))

    values = sorted(values)
    Structs[name] = values


def execute_config(filename):
    global Structs

    Structs = {}
    context = {
        'Struct': add_struct,
    }

    with open(filename) as f:
        exec(f.read(), context)

    return Structs


def get_struct_code(structname, structfields):
    members = []
    for member_name, member_type in structfields:
        members.append(StructMember.from_keyvalue(structname, member_name, member_type))

    return create_struct_functions(structname, members)


def create_includes(input_files, output):
    for input_file in input_files:
        structs = execute_config(input_file)

        for name in structs:
            outtxt = get_struct_code(name, structs[name])
            outfile_name = os.path.join(output, name + '.inc')
            dirname = os.path.dirname(outfile_name)
            util.mkdir(dirname)

            with open(outfile_name, 'w') as file:
                file.write(outtxt)
