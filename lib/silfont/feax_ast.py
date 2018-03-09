from fontTools.feaLib import ast
from fontTools.feaLib.ast import asFea

def asFea(g):
    if hasattr(g, 'asClassFea'):
        return g.asClassFea()
    elif hasattr(g, 'asFea'):
        return g.asFea()
    elif isinstance(g, tuple) and len(g) == 2:
        return asFea(g[0]) + "-" + asFea(g[1])   # a range
    elif g.lower() in ast.fea_keywords:
        return "\\" + g
    else:
        return g

ast.asFea = asFea

class ast_MarkClass(ast.MarkClass):
    # This is better fixed upstream in parser.parse_glyphclass_ to handle MarkClasses
    def asClassFea(self, indent=""):
        return "[" + " ".join(map(asFea, self.glyphs)) + "]"

class ast_BaseClass(ast_MarkClass) :
    def asFea(self, indent="") :
        return "@" + self.name + " = [" + " ".join(map(asFea, self.glyphs.keys())) + "];"

class ast_BaseClassDefinition(ast.MarkClassDefinition):
    def asFea(self, indent="") :
        # like base class asFea
        return "# {}baseClass {} {} @{};".format(indent, self.glyphs.asFea(),
                                               self.anchor.asFea(), self.markClass.name)

class ast_MarkBasePosStatement(ast.MarkBasePosStatement):
    def asFea(self, indent=""):
        # handles members added by parse_position_base_ with feax syntax
        if isinstance(self.base, ast.MarkClassName): # flattens pos @BASECLASS mark @MARKCLASS
            res = ""
            for bcd in self.base.markClass.definitions:
                if res != "":
                    res += "\n{}".format(indent)
                res += "pos base {} {}".format(bcd.glyphs.asFea(), bcd.anchor.asFea())
                res += "".join(" mark @{}".format(m.name) for m in self.marks)
                res += ";"
        else: # like base class method
            res = "pos base {}".format(self.base.asFea())
            res += "".join(" {} mark @{}".format(a.asFea(), m.name) for a, m in self.marks)
            res += ";"
        return res

    def build(self, builder) :
        #TODO: do the right thing here (write to ttf?)
        pass

class ast_MarkMarkPosStatement(ast.MarkMarkPosStatement):
    # super class __init__() for reference
    # def __init__(self, location, baseMarks, marks):
    #     Statement.__init__(self, location)
    #     self.baseMarks, self.marks = baseMarks, marks

    def asFea(self, indent=""):
        # handles members added by parse_position_base_ with feax syntax
        if isinstance(self.baseMarks, ast.MarkClassName): # flattens pos @MARKCLASS mark @MARKCLASS
            res = ""
            for mcd in self.baseMarks.markClass.definitions:
                if res != "":
                    res += "\n{}".format(indent)
                res += "pos mark {} {}".format(mcd.glyphs.asFea(), mcd.anchor.asFea())
                for m in self.marks:
                    res += " mark @{}".format(m.name)
                res += ";"
        else: # like base class method
            res = "pos mark {}".format(self.baseMarks.asFea())
            for a, m in self.marks:
                res += " {} mark @{}".format(a.asFea() if a else "<anchor NULL>", m.name)
            res += ";"
        return res

    def build(self, builder):
        # builder.add_mark_mark_pos(self.location, self.baseMarks.glyphSet(), self.marks)
        #TODO: do the right thing
        pass

class ast_CursivePosStatement(ast.CursivePosStatement):
    # super class __init__() for reference
    # def __init__(self, location, glyphclass, entryAnchor, exitAnchor):
    #     Statement.__init__(self, location)
    #     self.glyphclass = glyphclass
    #     self.entryAnchor, self.exitAnchor = entryAnchor, exitAnchor

    def asFea(self, indent=""):
        if isinstance(self.exitAnchor, ast.MarkClass): # pos cursive @BASE1 @BASE2
            res = ""
            allglyphs = set(self.glyphclass.glyphSet())
            allglyphs.update(self.exitAnchor.glyphSet())
            for g in sorted(allglyphs):
                entry = self.glyphclass.glyphs.get(g, None)
                exit = self.exitAnchor.glyphs.get(g, None)
                if res != "":
                    res += "\n{}".format(indent)
                res += "pos cursive {} {} {};".format(g,
                            (entry.anchor.asFea() if entry else "<anchor NULL>"),
                            (exit.anchor.asFea() if exit else "<anchor NULL>"))
        else:
            res = super(ast_CursivePosStatement, self).asFea(indent)
        return res

    def build(self, builder) :
        #TODO: do the right thing here (write to ttf?)
        pass

#similar to ast.MultipleSubstStatement
#one-to-many substitution, one glyph class is on LHS, multiple glyph classes may be on RHS
# equivalent to generation of one stmt for each glyph in the LHS class
# that's matched to corresponding glyphs in the RHS classes
#prefix and suffx are for contextual lookups and do not need processing
#replacement could contain multiple slots
#TODO: below only supports one RHS class?
class ast_MultipleSubstStatement(ast.Statement):
    def __init__(self, prefix, glyph, suffix, replacement, location=None):
        ast.Statement.__init__(self, location)
        self.prefix, self.glyph, self.suffix = prefix, glyph, suffix
        self.replacement = replacement
        if len(self.glyph.glyphSet()) > 1 :
            for i, r in enumerate(self.replacement) :
                if len(r.glyphSet()) > 1 :
                    self.multindex = i #first RHS slot with a glyph class
                    break
        else :
            self.multindex = 0

    def build(self, builder):
        prefix = [p.glyphSet() for p in self.prefix]
        suffix = [s.glyphSet() for s in self.suffix]
        glyphs = self.glyph.glyphSet()
        replacements = self.replacement[self.multindex].glyphSet()
        for i in range(min(len(glyphs), len(replacements))) :
            builder.add_multiple_subst(
                self.location, prefix, glyphs[i], suffix,
                self.replacement[0:self.multindex] + [replacements[i]] + self.replacement[self.multindex+1:])

    def asFea(self, indent=""):
        res = ""
        pres = " ".join(map(asFea, self.prefix)) if len(self.prefix) else ""
        sufs = " ".join(map(asFea, self.suffix)) if len(self.suffix) else ""
        glyphs = self.glyph.glyphSet()
        replacements = self.replacement[self.multindex].glyphSet()
        for i in range(min(len(glyphs), len(replacements))) :
            res += ("\n" + indent if i > 0 else "") + "sub "
            if len(self.prefix) > 0 or len(self.suffix) > 0 :
                if len(self.prefix) :
                    res += pres + " "
                res += asFea(glyphs[i]) + "'"
                if len(self.suffix) :
                    res += " " + sufs
            else :
                res += asFea(glyphs[i])
            res += " by "
            res += " ".join(map(asFea, self.replacement[0:self.multindex] + [replacements[i]] + self.replacement[self.multindex+1:]))
            res += ";" 
        return res


# similar to ast.LigatureSubstStatement
# many-to-one substitution, one glyph class is on RHS, multiple glyph classes may be on LHS
# equivalent to generation of one stmt for each glyph in the RHS class
# that's matched to corresponding glyphs in the LHS classes
# it's unclear which LHS class should correspond to the RHS class
# prefix and suffx are for contextual lookups and do not need processing
# replacement could contain multiple slots
#TODO: below only supports one LHS class?
class ast_LigatureSubstStatement(ast.Statement):
    def __init__(self, prefix, glyphs, suffix, replacement,
                 forceChain, location=None):
        ast.Statement.__init__(self, location)
        self.prefix, self.glyphs, self.suffix = (prefix, glyphs, suffix)
        self.replacement, self.forceChain = replacement, forceChain
        if len(self.replacement.glyphSet()) > 1:
            for i, g in enumerate(self.glyphs):
                if len(g.glyphSet()) > 1:
                    self.multindex = i #first LHS slot with a glyph class
                    break
        else:
            self.multindex = 0

    def build(self, builder):
        prefix = [p.glyphSet() for p in self.prefix]
        glyphs = [g.glyphSet() for g in self.glyphs]
        suffix = [s.glyphSet() for s in self.suffix]
        replacements = self.replacement.glyphSet()
        glyphs = self.glyphs[self.multindex].glyphSet()
        for i in range(min(len(glyphs), len(replacements))):
            builder.add_ligature_subst(
                self.location, prefix,
                self.glyphs[:self.multindex] + glyphs[i] + self.glyphs[self.multindex+1:],
                suffix, replacements[i], self.forceChain)

    def asFea(self, indent=""):
        res = ""
        pres = " ".join(map(asFea, self.prefix)) if len(self.prefix) else ""
        sufs = " ".join(map(asFea, self.suffix)) if len(self.suffix) else ""
        glyphs = self.glyphs[self.multindex].glyphSet()
        replacements = self.replacement.glyphSet()
        for i in range(min(len(glyphs), len(replacements))) :
            res += ("\n" + indent if i > 0 else "") + "sub "
            if len(self.prefix) > 0 or len(self.suffix) > 0 :
                if len(self.prefix) :
                    res += pres + " "
                res += " ".join(asFea(g) + "'" for g in self.glyphs[:self.multindex] + [glyphs[i]] + self.glyphs[self.multindex+1:])
                if len(self.suffix) :
                    res += " " + sufs
            else :
                res += " ".join(map(asFea, self.glyphs[:self.multindex] + [glyphs[i]] + self.glyphs[self.multindex+1:]))
            res += " by "
            res += asFea(replacements[i])
            res += ";"
        return res

class ast_IfBlock(ast.Block):
    def __init__(self, testfn, name, location=None):
        ast.Block.__init__(self, location=location)
        self.testfn = testfn
        self.name = name

    def asFea(self, indent=""):
        if self.testfn():
            return ast.Block.asFea(self, indent=indent)
        else:
            return ""
