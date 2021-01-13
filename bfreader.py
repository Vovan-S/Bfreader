import numpy as np
import sys

from binary_function import BinaryFunction, DNF


class Reader:
    name: str
    inputs: list
    inputs_comments: list
    outputs: list
    outputs_comments: list
    aliases: dict
    table_str: dict
    table: dict
    str_chr = chr(200)
    bfs: list
    cfg = {}
    cfg_filename = 'cfg.txt'

    def __init__(self, filename=None):
        self.name = None
        self.inputs = []
        self.inputs_comments = []
        self.outputs = []
        self.outputs_comments = []
        self.aliases = {}
        self.table_str = {}
        self.table = {}
        self.bfs = []

        self.line_counter = 0
        if filename != None:
            self.read(filename)
            self.eval_bfs()
        if len(self.cfg) == 0:
            self.load_cfg()

    def syntax_error(self, message):
        if self.line_counter > 0:
            raise SyntaxError(f'Syntax error at line {self.line_counter}: {message}!')
        else:
            raise SyntaxError(f'Syntax error: {message}!')

    def read(self, filename):
        self.line_counter = 1
        with open(filename, encoding='utf-8') as f:
            state = 'empty'
            for line in f:
                state = self.process_line(line, state, [])
                self.line_counter += 1
        self.line_counter = 0
        if len(self.table) == 0:
            for key in self.table_str:
                self.add_table_row(key)

    def load_cfg(self):
        with open(self.cfg_filename, encoding='utf-8') as f:
            for line in f:
                tokens = [t.strip() for t in line.split('=')]
                if len(tokens) != 2:
                    raise ValueError(f"Cfg error, invalid line: {line}")
                self.cfg[tokens[0]] = tokens[1]
                
            
    def add_table_row(self, table_string_key):
        var = self.str_to_bits(table_string_key)
        val = self.str_to_bits(self.table_str[table_string_key])
        floats = []
        for i in range(len(var)):
            if var[i] == -1:
                floats.append(i)
        if len(floats) == 0:
            if var in self.table:
                self.syntax_error(f'table collision "{table_string_key}"')
            self.table[var] = val
        else:
            for i in range(1 << len(floats)):
                new_var = list(var)
                for k in range(len(floats)):
                    if i & 1 << k > 0:
                        new_var[floats[k]] = 1
                    else:
                        new_var[floats[k]] = 0
                new_var = tuple(new_var)
                if new_var in self.table:
                    self.syntax_error(f'table collision "{table_string_key}"')
                self.table[new_var] = val

    @staticmethod
    def expand(line, strings):
        while line.find(Reader.str_chr) >= 0:
            line = line.replace(line, strings[0], 1)
            del strings[0]
        return line.strip()

    def process_line(self, line, state, strings):
        if len(line) == 0:
            return state
        line = line.strip()
        comment = line.find('#')
        string = line.find('"')
        if comment >= 0 and (string == -1 or comment < string):
            return self.process_line(line[:comment], state, strings)
        elif string >= 0:
            string2 = line.find('"', string + 1)
            if string2 < 0:
                self.syntax_error('cannot find closing \'"\'')
            s = line[string + 1: string2]
            strings.append(s)
            print("Replacing string, before:", line)
            line = line.replace('"' + s + '"', self.str_chr)
            print("Replacing string, after:", line)
            return self.process_line(line, state, strings)
        lines = line.split(';')
        if len(lines) > 1:
            c = 0
            for l in lines:
                strs = l.count(self.str_chr)
                state = self.process_line(l, state, strings[c:c+strs])
                c += strs
            return state
        print('Processing line:', line)
        # ожидается ввод ключевого слова
        if state == 'empty':
            if line.startswith("name:"):
                if self.name != None:
                    self.syntax_error('redefining name')
                line = line.lstrip('name:').strip()
                if len(line) == 0:
                    return 'name'
                else:
                    self.name = self.expand(line, strings)
                    return 'empty'
            elif line.startswith("inputs:"):
                print('Entered inputs')
                if len(self.inputs) > 0:
                    self.syntax_error('redefining inputs')
                line = line.lstrip('inputs:').strip()
                if len(line) == 0:
                    return 'inputs'
                else:
                    print('inputs recursion:', line)
                    return self.process_line(line, 'inputs', strings)
            elif line.startswith("aliases:"):
                line = line.lstrip('aliases:').strip()
                if len(line) == 0:
                    return 'aliases'
                else:
                    return self.process_line(line, 'aliases', strings)
            elif line.startswith("outputs:"):
                if len(self.outputs) > 0:
                    self.syntax_error('redefining outputs')
                line = line.lstrip('outputs:').strip()
                if len(line) == 0:
                    return 'outputs'
                else:
                    return self.process_line(line, 'outputs', strings)
            elif line.startswith("function:"):
                if len(self.table) > 0:
                    self.syntax_error('redefining function')
                line = line.lstrip('function:').strip()
                if len(line) == 0:
                    return 'function'
                else:
                    return self.process_line(line, 'function', strings)
            else:
                self.syntax_error(f'unknown keyword "{line.split()[0]}"')
        elif state == 'name':
            self.name = self.expand(line, strings)
            return 'empty'
        elif state == 'inputs':
            if line.find(':') >= 0:
                if len(self.inputs) == 0:
                    self.syntax_error("expected inputs")
                return self.process_line(line, 'empty', strings)
            tokens = line.split()
            if len(tokens) > 2:
                self.syntax_error(f'unexpected token "{tokens[2]}"')
            self.inputs.append(self.expand(tokens[0], strings))
            comment = ''
            if len(tokens) > 1:
                comment = self.expand(tokens[1], strings)
            self.inputs_comments.append(comment)
            return 'inputs'
        elif state == 'aliases':
            if line.find(':') >= 0:
                if len(self.aliases) == 0:
                    self.syntax_error("expected aliases")
                return self.process_line(line, 'empty', strings)
            tokens = line.split()
            if len(tokens) != 2:
                self.syntax_error(f'expected exactly two tokens insted of {len(tokens)}')
            if tokens[0] in self.aliases:
                self.syntax_error(f'redefining alias "{tokens[0]}"')
            if not tokens[0][0].isalpha():
                self.syntax_error(f'invalid alias name "{tokens[0]}"')
            bits = self.str_to_bits(self.expand(tokens[1], strings))
            self.aliases[tokens[0]] = bits
            return 'aliases'
        elif state == 'outputs':
            if line.find(':') >= 0:
                if len(self.outputs) == 0:
                    self.syntax_error("expected outputs")
                return self.process_line(line, 'empty', strings)
            tokens = line.split()
            if len(tokens) > 2:
                self.syntax_error(f'unexpected token "{tokens[2]}"')
            self.outputs.append(self.expand(tokens[0], strings))
            comment = ''
            if len(tokens) > 1:
                comment = self.expand(tokens[1], strings)
            self.outputs_comments.append(comment)
            return 'outputs'
        elif state == 'function':
            if line.find(':') >= 0:
                if len(self.table) == 0:
                    self.syntax_error("expected function defenition")
                return self.process_line(line, 'empty', strings)            
            tokens = line.split('|')
            if len(tokens) != 2:
                self.syntax_error('should have <vars> | <values>')
            tokens = [t.strip() for t in tokens]
            self.table_str[tokens[0]] = tokens[1]
            if len(self.aliases) > 0:
                self.add_table_row(tokens[0])
            return 'function'
        else:
            raise ValueError(f'Invalid state: {state}')
    

    def str_to_bits(self, string):
        res = []
        tokens = string.split()
        for t in tokens:
            if t in self.aliases:
                res.extend(self.aliases[t])
                continue
            for c in t:
                if c == '0':
                    res.append(0)
                elif c == '1':
                    res.append(1)
                elif c == '*':
                    res.append(-1)
                else:
                    self.syntax_error(f'invalid format of bitstring "{t}"')
        return tuple(res)

    def eval_bfs(self):
        m = len(self.outputs)
        n = len(self.inputs)
        floating = tuple(-1 for _ in range(m))
        vectors = np.full((1 << n, m), floating)
        for var in self.table:
            index = 0
            for i in range(n):
                if var[n - 1 - i] == 1:
                    index |= 1 << i
            vectors[index] = self.table[var]
        for vector in zip(*vectors):
            self.bfs.append(BinaryFunction(len(self.inputs), vector))

    @staticmethod
    def plus_notation(s, dollars=True):
        if s[0] == '+':
            s = s[1:]
            i = 0
            while s[-(i + 1)].isdigit():
                i += 1
            if i > 0:
                s = s[:-i] + "_{" + s[-i:] + "}"
            if dollars:
                s = '$' + s + '$'
        return s 

    """
    Вывод таблицы истинности функций на печать.
    Параметры:
     file  - либо открытый файл функцией open,
             либо строка с путем к файлу, этот файл будет перезаписан,
             либо None, в этом случае печать будет в консоль.

     local_cfg - параметры конфигурации, которые будут использованы
                 только в этом вызове. Должны быть строкой в формате:
                 "<имя параметра1> = <значение1>, <имя параметра2> = <значение2>, ..."

    Связанные параметры конфигурации:
     table_placment  [flag]         - одно из значений: h, t, b, h! и тд. для
                                      настройки расположения таблицы на странице.
     bold_headers    [true / false] - заголовки таблицы будут жирными.
     horisontal_bars [true / false] - строки таблицы истинности будут отделены линиями.
     vars_bar        [true / false] - столбцы переменных будут отделены линиями.
     vals_bar        [true / false] - столбцы значений будут отделены линиями.
     separator_double_bar     [t/f] - переменные и значения будут отделены двойной линией.
     boundaries      [true / false] - таблица будет в рамке.
     caption         [string]       - название таблицы; если будет пустое, названием
                                      будет считаться поле name.
     add_comments    [true / false] - добавление комментариев из исходного файла в название.
     label_prefix    [string]       - префикс метки tex.
     label           [string]       - метка tex.
     positioning     [\tex]         - команда выполняется внутри table.
     vars_positioning [flag]        - одно из значений: c, l, r, для выравнивания стобцов
                                      переменных.
     vals_positioning [flag]        - аналогично vars_positioning для столбцов значений.
     floating_str    [string]       - значение, которое будет подставлено в таблицу на
                                      место неопределенных значений.
     use_plus_notation        [t/f] - использования "плюс-нотации" для переменных
                                      входа и выхода (см. описание класса).
    """
    def print_table(self, local_cfg = None, file=None):
        cfg = self.cfg.copy()
        need_closing = False
        if file == None:
            file = sys.stdout
        elif isinstance(file, str):
            file = open(file, mode='w')
            need_closing = True
        write = lambda x: print(x, end='', file=file)
        if local_cfg != None:
            for line in local_cfg.split(','):
                tokens = [t.strip() for t in line.split('=')]
                if len(tokens) != 2:
                    raise ValueError(f"Cfg error, invalid line: {line}")
                cfg[tokens[0]] = tokens[1]
        nvars = len(self.inputs)
        nvals = len(self.outputs)
        write('\\begin{table}[' + cfg['table_placement'] + ']\n')
        write(cfg['positioning'] + '\n')
        write('\\begin{tabular}{')
        bounds = (cfg['boundaries'] == 'true')
        if bounds:
            write('|')
        pos = cfg['vars_positioning']
        write(pos)
        for i in range(1, nvars):
            if cfg['vars_bar'] == 'true':
                write('|')
            write(pos)
        write('||' if cfg['separator_double_bar'] == 'true' else '|')
        pos = cfg['vals_positioning']
        write(pos)
        for i in range(1, nvals):
            if cfg['vals_bar'] == 'true':
                write('|')
            write(pos)
        if bounds:
            write('|')
        write('}\n')
        if bounds:
            write('\\hline ')
        pn = cfg['use_plus_notation'] == 'true'
        bold = cfg['bold_headers'] == 'true'
        for var in self.inputs:
            s = var
            if pn:
                s = self.plus_notation(s)
            if bold:
                s = '\\textbf{' + s + '}'
            write(s + "& ")
        for val in self.outputs[:-1]:
            s = val
            if pn:
                s = self.plus_notation(s)
            if bold:
                s = '\\textbf{' + s + '}'
            write(s + " & ")
        s = self.outputs[-1]
        if pn:
            s = self.plus_notation(s)
        if bold:
            s = '\\textbf{' + s + '}'
        write(" " + s)
        bars = cfg['horisontal_bars'] == 'true'
        floating = cfg['floating_str']
        for i in range(1 << nvars):
            write(r'\\' + '\n')
            if bars or i == 0:
                write('\\hline ')
            for k in range(nvars):
                if i & (1 << (nvars - 1 - k)) > 0:
                    write('1 & ')
                else:
                    write('0 & ')
            for k in range(nvals - 1):
                v = self.bfs[k].value(i)
                write((floating if v == -1 else str(v)) + " & ")
            v = self.bfs[-1].value(i)
            write(floating if v == -1 else str(v))
        if bounds:
            write(r'\\' + '\n\\hline')
        write('\n\\end{tabular}\n')
        caption = cfg['caption']
        if caption == '-':
            caption = self.name if self.name != None else "Безымянная таблица"
        if cfg['add_comments'] == 'true':
            caption += '. \n'
            for i in range(nvars):
                s = self.inputs[i]
                s = self.plus_notation(s) if pn else s
                if len(self.inputs_comments[i]) > 0:
                    caption += s + ' --- ' + self.inputs_comments[i] + ';\n'
            for i in range(nvals):
                s = self.outputs[i]
                s = self.plus_notation(s) if pn else s
                if len(self.outputs_comments[i]) > 0:
                    caption += s + ' --- ' + self.outputs_comments[i]
        index = caption.find(';', len(caption) - 4)
        if index >= 0:
            caption = caption[:index] + '.'
        write('\\caption{' + caption + '}\n')
        label = cfg['label']
        label = '1' if label == '-' else label
        prefix = cfg['label_prefix']
        prefix = '' if prefix == '-' else prefix
        write('\\label{' + prefix + label + '}\n\\end{table}\n')
        if need_closing:
            file.close()


    """
    Вывод математических формул всех ДНФ для фукнции на печать.
    Параметры:
     file  - либо открытый файл функцией open,
             либо строка с путем к файлу, этот файл будет перезаписан,
             либо None, в этом случае печать будет в консоль.

     local_cfg - параметры конфигурации, которые будут использованы
                 только в этом вызове. Должны быть строкой в формате:
                 "<имя параметра1> = <значение1>, <имя параметра2> = <значение2>, ..."

    Связанные параметры конфигурации:
     and            [\tex] - команда для отображения конъюнкции
     or             [\tex] - команда для отображения дизъюнкции
     not            [\tex] - команда для отображения отрицания.
                             Будет использована так \tex{<выражение>}
     equation_begin [\tex] - Формула будет помещена между equation_begin и
     equation_end   [\tex] -          equation_end
     use_plus_notation [t/f]- использования "плюс-нотации" для переменных
                                      входа и выхода (см. описание класса).

    """
    def print_dnfs(self, local_cfg = None, file=None):
        cfg = self.cfg.copy()
        need_closing = False
        if file == None:
            file = sys.stdout
        elif isinstance(file, str):
            file = open(file, mode='w')
            need_closing = True
        write = lambda x: print(x, end='', file=file)
        if local_cfg != None:
            for line in local_cfg.split(','):
                tokens = [t.strip() for t in line.split('=')]
                if len(tokens) != 2:
                    raise ValueError(f"Cfg error, invalid line: {line}")
                cfg[tokens[0]] = tokens[1]
        nvars = len(self.inputs)
        nvals = len(self.outputs)
        pn = cfg['use_plus_notation'] == 'true'
        and_str = cfg['and']
        and_str = '' if and_str == '-' else and_str
        or_str = cfg['or']
        or_str = '' if or_str == '-' else or_str
        not_str = cfg['not']
        for i in range(nvals):
            write(cfg['equation_begin'])
            f = self.outputs[i]
            write(self.plus_notation(f, False) if pn else f)
            write(' = ')
            dnf = self.bfs[i].get_dnf()
            first = True
            if len(dnf.conjuncts) == 0:
                write(' 0 ')
            else:
                for c in dnf.conjuncts:
                    if not first:
                        write("\n" + or_str + " ")
                    else:
                        first = False
                    for j in range(len(c)):
                        if c[j] != -1:
                            var = self.inputs[j]
                            var = self.plus_notation(var, False) if pn else var
                            if c[j] == 0:
                                var = not_str + "{" + var + "}"
                            if j > 0:
                                write(and_str)
                            write(var)
            write(cfg['equation_end'] + '\n')
        if need_closing:
            file.close()

    """
    Выводит команды для генерации рисунка логической схемы для
    выбранных ДНФ.
    Для отображения используется пакет tikz для latex.

    Параметры:
     file  - либо открытый файл функцией open,
             либо строка с путем к файлу, этот файл будет перезаписан,
             либо None, в этом случае печать будет в консоль.

     which - ДНФ для печати:
             либо объект slice,
             либо итерируемый объект с индексами 0..n-1,
             где n - кол-во входов,
             либо None, тогда рисуются все ДНФ

     local_cfg - параметры конфигурации, которые будут использованы
                 только в этом вызове. Должны быть строкой в формате:
                 "<имя параметра1> = <значение1>, <имя параметра2> = <значение2>, ..."

    Связанные параметры конфигурации:
     optimize_circuit   [true / false] - если true, то повторяющиеся конъюнкты будут
                                         исключены; актуально, если выходов > 1.
     element_width      [cm]           - ширина логического элемента в сантиметрах
     element_min_height [cm]           - минимальная высота логического элемента
     invertor_height    [cm]           - высота инвертора
     between_wiring     [cm]           - расстояние между идущими рядом проводами
     dots_radius        [cm]           - радиус черных точек, обозначающих разветвление
                                         провода
     inversion_radius   [cm]           - радиус кружка инвертора
     element_vspace     [cm]           - расстояние между элементами по вертикали
     element_hspace     [cm]           - расстояние между элементами по горизонтали
     use_plus_notation  [true / false] - использования "плюс-нотации" для переменных
                                         входа и выхода (см. описание класса).

    """
    def draw_dnf(self, which=None, local_cfg=None, file=None):
        cfg = self.cfg.copy()
        need_closing = False
        if file == None:
            file = sys.stdout
        elif isinstance(file, str):
            file = open(file, mode='w')
            need_closing = True
        write = lambda x: print(x, end='', file=file)
        if local_cfg != None:
            for line in local_cfg.split(','):
                tokens = [t.strip() for t in line.split('=')]
                if len(tokens) != 2:
                    raise ValueError(f"Cfg error, invalid line: {line}")
                cfg[tokens[0]] = tokens[1]
        dnfs = []
        outs = []
        if which == None:
            dnfs = [f.get_dnf() for f in self.bfs]
            outs = self.outputs
        elif isinstance(which, slice):
            dnfs = [f.get_dnf() for f in self.bfs[which]]
            outs = self.outputs[which]
        else:
            try:
                dnfs = [self.bfs[i].get_dnf() for i in which]
                outs = [self.outputs[i] for i in which]
            except:
                raise ValueError('Invalid value of "which"!')
        opt = cfg['optimize_circuit'] == 'true'
        ands = []
        has_repeated = False
        n_ands = 0
        # считаем количество элементов И
        for dnf in dnfs:
            for c in dnf.conjuncts:
                if not opt or c not in ands:
                    n_ands += 1
                else:
                    has_repeated = True
        # матрица смежности вход - элемент И
        in_and = np.zeros((len(self.inputs), n_ands))
        # матрица смежности элемент И - выход
        and_out = np.zeros((n_ands, len(outs)))
        # количество переменных в И
        and_sums = np.zeros((n_ands,))
        in_sums = np.zeros(len(self.inputs))
        out_sums = np.zeros(len(outs))
        for i in range(len(dnfs)):
            for c in dnfs[i].conjuncts:
                index = len(ands)
                if not opt or c not in ands:
                    ands.append(c)
                    for j in range(len(c)):
                        if c[j] == 1:
                            in_and[j][index] = 1
                            and_sums[index] += 1
                            in_sums[j] += 1
                        elif c[j] == 0:
                            in_and[j][index] = -1
                            and_sums[index] += 1
                            in_sums[j] += 1
                else:
                    #ands_repeat.append(c)
                    index = ands.index(c)
                and_out[index][i] = 1
                out_sums[i] += 1
        # шаг между проводами
        step = float(cfg['between_wiring'])
        # float x -> 'x cm'
        cm = lambda f: str(f)[:15].rstrip('0') + 'cm' if f != 0 else '0'
        # радиус кружочков
        rad = float(cfg['dots_radius'])
        irad = float(cfg['inversion_radius'])
        # минимальная высота элемента
        min_height = float(cfg['element_min_height'])
        iheight = float(cfg['invertor_height'])
        # ширина элемента
        width = float(cfg['element_width'])
        hspace = float(cfg['element_hspace'])
        vspace = float(cfg['element_vspace'])
        y = 0
        x = 0
        ands_y = np.zeros_like(and_sums)
        ins_x = np.zeros_like(in_sums)
        for i in range(1, len(in_sums) + 1):
            if in_sums[-i] == 0:
                continue
            ins_x[-i] = x
            x -= step
        in_draw = [[] for _ in in_sums]
        x = hspace
        # начинаем рисовать 
        write('\\begin{tikzpicture}\n')
        # сначала рисуем элементы
        for i in range(n_ands):
            #out_x = x + width + hspace + i * step
            # нет входов - ничего не рисуем
            if and_sums[i] == 0:
                continue
            # один вход
            elif and_sums[i] == 1:
                inverted = False
                for j in range(len(in_sums)):
                    if in_and[j][i] != 0:
                        inverted = in_and[j][i] < 0
                        break
                # надо нарисовать инвертор
                if inverted:
                    write(f'\\draw[thick] ({cm(x)}, {cm(y)}) rectangle ({cm(x + width)}, {y - iheight});\n')
                    #write(f'\\draw ({cm(x + width)}, {cm(y - iheight *0.5)}) -- ({cm(out_x)}, {cm(y - iheight *0.5)});\n')
                    #write(f'\\draw[fill=white] ({cm(x + width)}, {cm(y - iheight *0.5)}) circle ({cm(irad)});\n')
                    write(f'\\node [below] at ({cm(x + 0.5 * width)}, {cm(y)}) ' + '{1};\n')
                    ands_y[i] = y - iheight * 0.5
                    y -= iheight
                    in_draw[j].append((ands_y[i], False))
                    # отметим, что тут стоит инвертор
                    and_sums[i] = -1 # забыл зачем
                # просто провод
                else:
                    write(f'\\draw ({cm(x)}, {cm(y)}) -- ({cm(x + width)}, {cm(y)});\n')
                    ands_y[i] = y
                    in_draw[j].append((y, False))
            # надо рисовать элемент И
            else:
                dy = (min_height - and_sums[i] * step) / 2
                height = min_height
                if dy < 0:
                    height = and_sums[i] * step
                    dy = 0
                dy += step / 2
                c = 0
                for j in range(len(in_sums)):
                    v = in_and[j][i]
                    if v != 0:
                        in_draw[j].append((y - dy - c * step, v == -1))
                        c += 1
                write(f'\\draw[thick] ({cm(x)}, {cm(y)}) rectangle ({cm(x + width)}, {cm(y - height)});\n')
                #write(f'\\draw ({cm(x + width)}, {cm(y - height *0.5)}) -- ({cm(out_x)}, {cm(y - height *0.5)});\n')
                write(f'\\node [below] at ({cm(x + 0.5*width)}, {cm(y)}) ' + '{$\&$};\n')
                ands_y[i] = y - 0.5*height
                y -= height
            y -= vspace
        lowest = y + vspace
        pn = cfg['use_plus_notation'] == 'true'
        # теперь рисуем проводку
        for j in range(len(in_draw)):
            if len(in_draw[j]) == 0:
                continue
            x1 = ins_x[j]
            y1 = vspace
            x2 = hspace
            y2 = in_draw[j][-1][0]
            in_name = self.plus_notation(self.inputs[j]) if pn else self.inputs[j]
            write(f'\\draw ({cm(x1)}, {cm(y1)}) node [above] ' + '{' + in_name + '}' + f' -- ({cm(x1)}, {cm(y2)}) -- ({cm(x2)}, {cm(y2)});\n')
            for y, _ in in_draw[j][:-1]:
                write(f'\\draw ({cm(x1)}, {cm(y)}) -- ({cm(x2)}, {cm(y)});\n')
                write(f'\\filldraw [black] ({cm(x1)}, {cm(y)}) circle ({cm(rad)});\n')
            for y, invert in in_draw[j]:
                if invert:
                    write(f'\\draw[fill=white] ({cm(x2)}, {cm(y)}) circle ({cm(irad)});\n')
        outs_height = (len(outs) - 1) * vspace
        for i in range(len(outs)):
            outs_height += max(out_sums[i] * step, min_height)
        out_draw = [[] for _ in and_sums]
        y = (lowest + outs_height) / 2
        x = 3 * hspace + width + (len(and_sums) - 1) * step
        # рисуем выходные ИЛИ
        for i in range(len(outs)):
            height = min_height
            dy = (min_height - out_sums[i] * step) / 2
            if dy < 0:
                dy = 0
                height = out_sums[i] * step
            dy += step / 2
            write(f'\\draw[thick] ({cm(x)}, {cm(y)}) rectangle ({cm(x + width)}, {cm(y - height)});\n')
            write(f'\\node [below] at ({cm(x + 0.5*width)}, {cm(y)}) ' + '{' + '1' + '};\n')
            outname = self.plus_notation(outs[i]) if pn else outs[i]
            write(f'\\draw ({cm(x + width)}, {cm(y - height*0.5)}) -- ({cm(x + width + hspace)}, {cm(y - height*0.5)}) node '
                  + '[right] {' + outname + '};\n')
            c = 0
            for j in range(len(and_sums)):
                if and_out[j][i] > 0:
                    out_draw[j].append(y - dy - c * step)
                    c += 1
            y -= height + vspace
        # попытаемся найти расположение проводов без конфликтов
        xs = np.zeros_like(and_sums)
        if len(outs) == 1:
            c = len(and_sums) - 1
            i = 0
            for ot in range(len(outs)):
                end = i + 1
                while end < len(and_sums) and and_out[end][ot] > 0:
                    end += 1
                j = end
                while i < j:
                    xs[i] = 2 * hspace + width + c * step
                    c -= 1; i += 1
                    if i < j:
                        xs[j - 1] = 2 * hspace + width + c * step
                        j -= 1; c -= 1
                i = end
        else:
            # отношение "заслоняет"
            # x заслоняет y если один из концов x находится
            # на одной высоте с началом y
            covers = np.zeros((len(and_sums), len(and_sums)))
            for i in range(len(and_sums)):
                for j in range(len(and_sums)):
                    if i == j:
                        continue
                    for i_tail in out_draw[i]:
                        if abs(i_tail - ands_y[j]) < step:
                            covers[i][j] = 1
            #print(covers)
            c = len(and_sums) - 1
            picked = set()
            while len(picked) < len(and_sums):
                index = 0
                min_covered = len(and_sums)
                # будем ставить дальше те линии, которые никто не заслоняет
                for i in range(len(and_sums)):
                    if i in picked:
                        continue
                    n_covered = 0
                    for j in range(len(and_sums)):
                        if j in picked:
                            continue
                        if covers[j][i] > 0:
                            n_covered += 1
                    if n_covered == 0:
                        min_covered = n_covered
                        index = i
                        break
                    elif n_covered < min_covered:
                        min_covered = n_covered
                        index = i
                if min_covered > 0:
                    print('Warning! Cannot find cables placement without collisions!')
                xs[index] = 2 * hspace + width + c * step
                c -= 1
                picked.add(index)
        #print(sorted(xs))
                
        # теперь рисуем проводку
        for i in range(len(out_draw)):
            if len(out_draw[i]) == 0:
                continue
            y1 = ands_y[i]
            x1 = xs[i]
            write(f'\\draw ({cm(hspace + width)}, {cm(y1)}) -- ({cm(x1)}, {cm(y1)});\n')
            if and_sums[i] < 0:
                write(f'\\draw[fill=white] ({cm(hspace + width)}, {cm(y1)}) circle ({cm(irad)});\n')
            j = 0
            while j < len(out_draw[i]) and out_draw[i][j] >= y1:
                y2 = out_draw[i][j]
                if j == 0:
                    write(f'\\draw ({cm(x1)}, {cm(y1)}) -- ({cm(x1)}, {cm(y2)}) -- ({cm(x)}, {cm(y2)});\n')
                else:
                    write(f'\\draw ({cm(x1)}, {cm(y2)}) -- ({cm(x)}, {cm(y2)});\n')
                    write(f'\\filldraw [black] ({cm(x1)}, {cm(y2)}) circle ({cm(rad)});\n')
                j += 1
            while j < len(out_draw[i]):
                y2 = out_draw[i][j]
                if j == len(out_draw[i]) - 1:
                    write(f'\\draw ({cm(x1)}, {cm(y1)})-- ({cm(x1)}, {cm(y2)}) -- ({cm(x)}, {cm(y2)});\n')
                else:
                    write(f'\\draw ({cm(x1)}, {cm(y2)}) -- ({cm(x)}, {cm(y2)});\n')
                    write(f'\\filldraw [black] ({cm(x1)}, {cm(y2)}) circle ({cm(rad)});\n')
                j += 1
        write('\\end{tikzpicture}\n')
        if need_closing:
            file.close()
        
        

            
            
        
        
        

        
        
        
if __name__ == "__main__":
    r = Reader('functions/one-digit.txt')
    #print("name:", r.name)
    #print("inputs:", r.inputs)
    #print("inputs comments:", r.inputs_comments)
    #print("outputs:", r.outputs)
    #print("outputs comments:", r.outputs_comments)
    #print("aliases:", r.aliases)
    #print("table:", r.table)
    #print("f0:", r.bfs[0].values)
    r.print_table()
    r.print_dnfs()
    r.draw_dnf(file='figures.tex', which=(0, 1, 2))
    

    
                    
                
                
                    
    
