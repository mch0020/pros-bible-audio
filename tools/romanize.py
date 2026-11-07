"""Rough a-z spellings for the MMS aligner (it only needs to find where each
word is, so this follows the reader's pronunciation loosely)."""
import re, unicodedata
G = {'α':'a','β':'b','γ':'g','δ':'d','ε':'e','ζ':'z','η':'e','θ':'th','ι':'i','κ':'k','λ':'l','μ':'m','ν':'n','ξ':'x',
     'ο':'o','π':'p','ρ':'r','σ':'s','ς':'s','τ':'t','υ':'u','φ':'ph','χ':'ch','ψ':'ps','ω':'o'}
def greek(w):
    d = unicodedata.normalize('NFD', w.lower()); rough = '̔' in d[:4]
    b = ''.join(c for c in d if unicodedata.category(c) != 'Mn')
    s = ''
    for c in b.replace('γγ', 'Ng').replace('γκ', 'Nk').replace('γχ', 'Nch').replace('ου', 'U'):
        s += {'N': 'n', 'U': 'ou'}.get(c) or G.get(c, c if c in 'kch' else '')
    return ('h' + s) if rough and s else s
# Hebrew
SHIN, SIN, DAG, HOLAM, SHURUK_DOT = 'ׁ', 'ׂ', 'ּ', 'ֹ', 'ּ'
V = {'ְ':'e','ֱ':'e','ֲ':'a','ֳ':'o','ִ':'i','ֵ':'e','ֶ':'e','ַ':'a','ָ':'a','ֹ':'o','ֺ':'o','ֻ':'u','ׇ':'o'}
C = {'א':'','ב':'v','ג':'g','ד':'d','ה':'h','ו':'v','ז':'z','ח':'kh','ט':'t','י':'y','כ':'kh','ך':'kh','ל':'l','מ':'m','ם':'m','נ':'n','ן':'n',
     'ס':'s','ע':'','פ':'f','ף':'f','צ':'ts','ץ':'ts','ק':'k','ר':'r','ש':'sh','ת':'t'}
HARD = {'ב':'b','כ':'k','ך':'k','פ':'p','ף':'p'}
def hebrew(w):
    d = unicodedata.normalize('NFD', w)
    d = ''.join(c for c in d if not ('֑' <= c <= '֯') and c not in 'ֽֿ׀׃ׅׄ')
    groups = []
    for c in d:
        if 'א' <= c <= 'ת': groups.append([c, ''])
        elif groups: groups[-1][1] += c
    out = []
    for i, (c, m) in enumerate(groups):
        last = i == len(groups) - 1
        if c == 'ו' and m == DAG and not ('ְ' <= m[:1] <= 'ֻ'): out.append('u'); continue
        if c == 'ו' and HOLAM in m and i > 0: out.append('o'); continue
        if c == 'ש': cons = 's' if SIN in m else 'sh'
        elif c in HARD and DAG in m: cons = HARD[c]
        else: cons = C.get(c, '')
        if c == 'ה' and last and DAG not in m: cons = ''
        if c == 'י' and not any(ch in V for ch in m) and i > 0: cons = ''
        vow = ''.join(V[ch] for ch in m if ch in V)
        if vow == 'e' and 'ְ' in m and not (i == 0): vow = ''
        if c == 'ח' and last and 'ַ' in m: out.append('a' + cons); continue  # furtive patah
        out.append(cons + vow)
    return re.sub('[^a-z]', '', ''.join(out))
if __name__ == '__main__':
    print([greek(w) for w in 'Βίβλος γενέσεως Ἰησοῦ Χριστοῦ υἱοῦ Ἀβραάμ ἐγέννησε'.split()])
    print([hebrew(w) for w in 'בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ וְרוּחַ מְרַחֶפֶת וַיֹּאמֶר יְהִי אוֹר'.split()])
