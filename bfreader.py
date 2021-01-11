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
            bits = self.str_to_bits(tokens[1])
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

    def print_table(self, local_cfg = None, file=None):
        cfg = self.cfg.copy()
        if file == None:
            file = sys.stdout
        elif isinstance(file, str):
            file = open(file, mode='w')
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
            
    def print_dnfs(self, local_cfg = None, file=None):
        cfg = self.cfg.copy()
        if file == None:
            file = sys.stdout
        elif isinstance(file, str):
            file = open(file, mode='w')
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
        
        
if __name__ == "__main__":
    r = Reader('functions/control.txt')
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
    

    
                    
                
                
                    
    
