import numpy as np

# Представление для двоичной функции
# values - список значений 0, 1, -1
# -1 - плавающее значение
class BinaryFunction:
    n_variables: int
    values: list

    def __init__(self, n_variables, values):
        self.n_variables = n_variables
        self.values = values

    def value(self, var):
        if isinstance(var, int):
            return self.values[var]
        if len(var) != self.n_variables:
            raise ValueError("Invalid dimansion")
        index = 0
        for i in range(self.n_variables):
            if var[i] == 1:
                index |= 1 << i
        if index < len(self.values):
            return self.values[index]
        else:
            return -1

    def get_sdnf(self, include_float=False):
        c = []
        for i in range(1 << self.n_variables):
            if self.values[i] == 1 or (include_float and self.values[i] == -1):
              c.append(tuple(1 if i & (1 << k) > 0 else 0
                             for k in range(self.n_variables)))
        return DNF(self.n_variables, c)

    def get_dnf(self):
        have_float = False
        for v in self.values:
            if v == -1:
                have_float = True
                break
        if have_float:
            dnf1 = self.get_sdnf().simplify()
            n = self.n_variables
            changed = True
            while changed:
                changed = False
                cs = dnf1.conjuncts
                #print('simplifying: ', dnf1.conjuncts)
                for k in range(len(cs)):
                    c = cs[k]
                    to_delete = -1
                    for i in range(n):
                        if c[i] == -1:
                            continue
                        a = []
                        absent = []
                        for j in range(n):
                            if i == j:
                                a.append(1 - c[j])
                            elif c[j] == -1:
                                a.append(0)
                                absent.append(j)
                            else:
                                a.append(c[j])
                        canDelete = True
                        for j in range(1 << len(absent)):
                            for s in range(len(absent)):
                                if j & (1 << s) > 0:
                                    a[absent[s]] = 1
                                else:
                                    a[absent[s]] = 0
                            if self.value(a) == 0:
                                canDelete = False
                        if canDelete:
                            to_delete = i
                            #print(a, to_delete)
                            break
                    if to_delete >= 0:
                        cs[k] = DNF.remove_var(c, to_delete)
                        changed = True
                #print('deleted some vars:', cs)
                dnf1 = dnf1.simplify()
            return dnf1
        else:
            return self.get_sdnf().simplify()
        

# ДНФ, хранится в виде списка кортежей (a1, a2... an),
# где n - количество переменных. ai = 1, если переменная входит
# без отрицания, = 0 если с отрицанием, = -1 если не входит
class DNF:
    n_variables: int
    conjuncts: list

    def __init__(self, n_variables, conjuncts):
        self.n_variables = n_variables
        # удаляем дубликаты
        self.conjuncts = list(set(conjuncts))

    @staticmethod
    def remove_var(conjunct, var):
        return tuple(conjunct[i] if i != var else -1
                for i in range(len(conjunct)))

    # возвращает копию, где ДНФ минимизирована
    # минимизация происходит по следующим правилам:
    # 1. [(x, 1), (x, 0)] = [(x, -1)]
    # 2. [(x, -1), (x, y)] = [(x, -1)]
    # 3. [(x, -1), (1 - x, y)] = [(x, -1), (-1, y)],
    #     x, y = 0 или 1
    def simplify(self):
        nc = self.conjuncts.copy()
        changed = True
        while changed:
            changed = False
            to_delete = None
            to_replace = None
            for c1 in nc:
                for c2 in nc:
                    if c1 == c2:
                        continue
                    diff = []
                    for i in range(self.n_variables):
                        if c1[i] != c2[i]:
                            diff.append(i)
                    # правило 2
                    n = [0, 0]
                    for i in diff:
                        if c1[i] == -1:
                            n[0] += 1
                        if c2[i] == -1:
                            n[1] += 1
                    if n[0] == len(diff):
                        toDelete = c2
                    elif n[1] == len(diff):
                        toDelete = c1
                    # правило 1
                    elif len(diff) == 1:
                        to_replace = (c1,
                                      self.remove_var(c1, diff[0]))
                        to_delete = c2
                    # правило 3
                    elif n[0] == len(diff) - 1:
                        last = 0
                        for i in diff:
                            if c1[i] != -1:
                                last = i
                                break
                        if c2[last] != -1:
                            to_replace = (c2, self.remove_var(c2, last))
                    elif n[1] == len(diff) - 1:
                        last = 0
                        for i in diff:
                            if c2[i] != -1:
                                last = i
                                break
                        if c1[last] != -1:
                            to_replace = (c1, self.remove_var(c1, last))
                    if to_replace != None or to_delete != None:
                        break
                if to_replace != None or to_delete != None:
                    break    
            if to_delete != None:
                nc.remove(to_delete)
                changed = True
            if to_replace != None:
                nc.remove(to_replace[0])
                nc.append(to_replace[1])
                changed = True
        return DNF(self.n_variables, nc)

    def merge(self, other):
        if self.n_variables != other.n_variables:
            raise ValueError("Invalid dimensions!")
        nc = self.conjuncts.copy()
        nc.extend(other.conjuncts)
        return DNF(self.n_variables, nc)

    def get_bf(self):
        values = []
        for i in range(1 << self.n_variables):
            c0 = tuple(1 if i & (1 << k) > 0 else 0
                       for k in range(self.n_variables))
            found = False
            for c in self.conjuncts:
                found = True
                for j in range(self.n_variables):
                    if c[j] != -1 and c0[j] != c[j]:
                        found = False
                        break
                if found:
                    break
            values.append(1 if found else 0)
        return BinaryFunction(self.n_variables, values)

if __name__ == "__main__":
    c = [(1, -1), (0, 1)]
    d1 = DNF(2, c)
    f = d1.get_bf()
    print(f.get_sdnf().conjuncts)
    print(f.get_dnf().conjuncts)
    
    
                        
                        
                        
        
