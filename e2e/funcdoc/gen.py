#!/usr/bin/env python3
"""Generate /tmp/funcdoc.json: seeds + per-function localized formulas with CORRECT arguments,
for the "functions check" spreadsheet. English-keyed arg templates (my knowledge of the signatures)
reference a typed seed area; localized names come from editor/po-funcnames.js (ru). The typer script
enters them into Collabora; errors are parsed from the saved xlsx and args fixed here, iteratively.

Args use ';' (RU arg separator) and reference seed cells (locale-independent). No decimal literals
(use seed cells / ints). No nested function names (would need localizing) — only cell refs + ints.
"""
import json, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
import json as _j
funcs = _j.load(open(os.path.join(HERE, "funcs.json"), encoding="utf-8"))  # [{en,cat,ru}]

# ---- Seed area (typed by the typer). cell -> value (str; formulas start with '='). ----
SEEDS = {
    "$BA$1": "5", "$BA$2": "3", "$BA$3": "2", "$BA$4": "4", "$BA$5": "10", "$BA$6": "100",
    "$BA$7": "=5/100",              # rate 0.05
    "$BA$8": "6", "$BA$9": "12", "$BA$10": "1", "$BA$11": "=1/2",
    "$BD$1": "=DATE(2024;1;15)", "$BD$2": "=DATE(2025;6;20)", "$BD$3": "=DATE(2020;3;1)",
    "$BE$1": "текст", "$BE$2": "Мир", "$BE$3": "123", "$BE$4": "a,b,c",
    "$BF$1": "=TRUE()", "$BF$2": "=FALSE()",
    "$BG$1": "4", "$BH$1": "3", "$BG$2": "6", "$BH$2": "3",     # matrix1 BG1:BH2 (det=-6)
    "$BI$1": "1", "$BJ$1": "2", "$BI$2": "3", "$BJ$2": "4",     # matrix2 BI1:BJ2
}
# numeric range BB1:BB10 = 1..10 ; range2 BC1:BC10 = 2..20 even
for i in range(1, 11):
    SEEDS[f"$BB${i}"] = str(i)
    SEEDS[f"$BC${i}"] = str(2 * i)
# DB block BA12:BC16 (header + 4 rows) ; criteria BA18:BA19
SEEDS.update({"$BA$12": "Кол", "$BB$12": "Цена", "$BC$12": "Год"})
for j, (k, c, y) in enumerate([(10, 100, 2020), (20, 200, 2021), (30, 150, 2022), (40, 300, 2023)]):
    r = 13 + j
    SEEDS[f"$BA${r}"] = str(k); SEEDS[f"$BB${r}"] = str(c); SEEDS[f"$BC${r}"] = str(y)
SEEDS["$BA$18"] = "Кол"; SEEDS["$BA$19"] = ">0"
# financial seeds: cashflow with a sign change AY1:AY5 (for IRR/NPV/MIRR), matching dates AY7:AY11
# (for XIRR/XNPV), a near maturity BD4 (<1yr, for T-bill), a rate schedule AX1:AX4 (for FVSCHEDULE)
for i, v in enumerate([-100, 30, 40, 50, 20]):
    SEEDS[f"$AY${i + 1}"] = str(v)
SEEDS.update({"$AY$7": "=DATE(2024;1;1)", "$AY$8": "=DATE(2024;4;1)", "$AY$9": "=DATE(2024;8;1)",
              "$AY$10": "=DATE(2025;1;1)", "$AY$11": "=DATE(2025;6;1)"})
SEEDS["$BD$4"] = "=DATE(2024;6;15)"
for i in range(1, 5):
    SEEDS[f"$AX${i}"] = "=5/100"

# ---- seed reference shorthands ----
S = dict(n="$BA$1", n2="$BA$2", n3="$BA$3", n4="$BA$4", ten="$BA$5", hun="$BA$6", rate="$BA$7",
         six="$BA$8", twelve="$BA$9", one="$BA$10", half="$BA$11",
         r1="$BB$1:$BB$10", r2="$BC$1:$BC$10", cell="$BB$1",
         d1="$BD$1", d2="$BD$2", d3="$BD$3", d4="$BD$4",
         cash="$AY$1:$AY$5", cashdates="$AY$7:$AY$11", rsched="$AX$1:$AX$4",
         t1="$BE$1", t2="$BE$2", tnum="$BE$3", csv="$BE$4", tr="$BE$1:$BE$2",
         b="$BF$1", m1="$BG$1:$BH$2", m2="$BI$1:$BJ$2", msq="$BG$1:$BH$2",
         db="$BA$12:$BC$16", dbfield="$BB$12", crit="$BA$18:$BA$19")

# ---- category default arg templates (type-aware; best common signature) ----
CAT_DEF = {
    "FINANCIAL": "({rate};{ten};-{hun})",
    "LOGICAL": "({b})",
    "TEXT": "({t1})",
    "DATEnTIME": "({d1})",
    "STATISTICAL": "({r1})",
    "DATABASE": "({db};{dbfield};{crit})",
    "INFORMATION": "({n})",
    "ARRAY": "({r1})",
    "SPREADSHEET": "({n})",
    "?": "({n})",  # math & trig — mostly 1 number
}

# ---- explicit per-function overrides (correct signatures). English name -> arg template. ----
OV = {
  # math & trig
  "ABS": "({n})", "SQRT": "({ten})", "POWER": "({n};{n2})", "MOD": "({ten};{n2})",
  "ROUND": "({rate};{n2})", "ROUNDUP": "({rate};{n2})", "ROUNDDOWN": "({rate};{n2})",
  "MROUND": "({ten};{n2})", "TRUNC": "({rate};{n2})", "INT": "({rate})", "SIGN": "({n})",
  # domain-sensitive trig/inverse (|x|<=1 etc.) -> use half=0.5
  "ACOS": "({half})", "ASIN": "({half})", "ATANH": "({half})", "FISHER": "({half})",
  "ACOSH": "({n})", "ACOTH": "({n})", "ATAN": "({n})", "ACOT": "({n})",
  "GCD": "({r1})", "LCM": "({r1})", "SUM": "({r1})", "SUMSQ": "({r1})", "PRODUCT": "({r1})",
  "SUMPRODUCT": "({r1};{r2})", "SUMX2MY2": "({r1};{r2})", "SUMX2PY2": "({r1};{r2})",
  "SUMXMY2": "({r1};{r2})", "SUMIF": "({r1};\">2\")", "SUMIFS": "({r1};{r1};\">2\")",
  "SQRTPI": "({n})", "FACT": "({n})", "FACTDOUBLE": "({n})", "COMBIN": "({ten};{n2})",
  "COMBINA": "({ten};{n2})", "PERMUT": "({ten};{n2})", "PERMUTATIONA": "({ten};{n2})",
  "MULTINOMIAL": "({r1})", "SERIESSUM": "({n};{n2};{n3};{r1})", "GCDGCD": "({r1})",
  "ATAN2": "({n};{n2})", "LOG": "({ten};{n2})", "ROMAN": "({ten})", "ARABIC": "(\"XII\")",
  "SUBTOTAL": "(9;{r1})", "AGGREGATE": "(9;0;{r1})", "CEILING": "({rate};{n2})",
  "FLOOR": "({rate};{n2})", "CEILING.MATH": "({rate})", "FLOOR.MATH": "({rate})",
  "CEILING.PRECISE": "({rate})", "FLOOR.PRECISE": "({rate})", "ISO.CEILING": "({rate})",
  # financial (LibreOffice signatures; dates: d1<d2, issue d3, near-maturity d4; cashflow with sign change)
  "PV": "({rate};{ten};-{ten})", "FV": "({rate};{ten};-{ten})", "PMT": "({rate};{ten};{hun})",
  "NPER": "({rate};-{ten};{hun})", "RATE": "({ten};-{ten};80)", "NPV": "({rate};{cash})",
  "IRR": "({cash})", "MIRR": "({cash};{rate};{rate})", "XIRR": "({cash};{cashdates})",
  "XNPV": "({rate};{cash};{cashdates})", "FVSCHEDULE": "({hun};{rsched})",
  "IPMT": "({rate};{n2};{ten};{hun})", "PPMT": "({rate};{n2};{ten};{hun})", "ISPMT": "({rate};{n2};{ten};{hun})",
  "CUMIPMT": "({rate};{ten};{hun};1;2;0)", "CUMPRINC": "({rate};{ten};{hun};1;2;0)",
  "SLN": "({hun};{ten};5)", "SYD": "({hun};{ten};5;{n2})", "DB": "({hun};{ten};5;{n2})",
  "DDB": "({hun};{ten};5;{n2})", "VDB": "({hun};{ten};5;0;{n2})",
  "AMORDEGRC": "({hun};{d3};{d1};{ten};{n2};{rate})", "AMORLINC": "({hun};{d3};{d1};{ten};{n2};{rate})",
  "EFFECT": "({rate};2)", "NOMINAL": "({rate};2)", "DOLLARDE": "({rate};16)", "DOLLARFR": "({rate};16)",
  "PDURATION": "({rate};{ten};{hun})", "RRI": "({ten};{ten};{hun})",
  "ACCRINT": "({d3};{d1};{d2};{rate};{hun};2)", "ACCRINTM": "({d3};{d2};{rate};{hun})",
  "COUPDAYBS": "({d1};{d2};2)", "COUPDAYS": "({d1};{d2};2)", "COUPDAYSNC": "({d1};{d2};2)",
  "COUPNCD": "({d1};{d2};2)", "COUPNUM": "({d1};{d2};2)", "COUPPCD": "({d1};{d2};2)",
  "DISC": "({d1};{d2};95;{hun})", "DURATION": "({d1};{d2};{rate};{rate};2)",
  "MDURATION": "({d1};{d2};{rate};{rate};2)", "INTRATE": "({d1};{d2};{hun};110)",
  "RECEIVED": "({d1};{d2};{hun};{rate})", "PRICE": "({d1};{d2};{rate};{rate};{hun};2)",
  "PRICEDISC": "({d1};{d2};{rate};{hun})", "PRICEMAT": "({d1};{d2};{d3};{rate};{rate})",
  "YIELD": "({d1};{d2};{rate};95;{hun};2)", "YIELDDISC": "({d1};{d2};95;{hun})",
  "YIELDMAT": "({d1};{d2};{d3};{rate};95)", "TBILLEQ": "({d1};{d4};{rate})",
  "TBILLPRICE": "({d1};{d4};{rate})", "TBILLYIELD": "({d1};{d4};95)",
  "ODDFPRICE": "({d1};{d2};{d3};{d4};{rate};{rate};{hun};2)", "ODDFYIELD": "({d1};{d2};{d3};{d4};{rate};95;{hun};2)",
  "ODDLPRICE": "({d1};{d2};{d3};{rate};{rate};{hun};2)", "ODDLYIELD": "({d1};{d2};{d3};{rate};95;{hun};2)",
  "QUOTIENT": "({ten};{n2})", "RANDBETWEEN": "({one};{ten})", "BASE": "({ten};{n2})",
  "DECIMAL": "(\"FF\";16)", "CONVERT": "({n};\"m\";\"ft\")", "EUROCONVERT": "({hun};\"DEM\";\"EUR\")",
  "COLOR": "({n};{n2};{n3})", "BITAND": "({ten};{six})", "BITOR": "({ten};{six})",
  "BITXOR": "({ten};{six})", "BITLSHIFT": "({ten};{n2})", "BITRSHIFT": "({ten};{n2})",
  # logical
  "NOT": "({b})", "AND": "({b};{b})", "OR": "({b};{b})", "XOR": "({b};{b})",
  "IF": "({b};{n};{n2})", "IFS": "({b};{n})", "IFERROR": "({n};0)", "IFNA": "({n};0)",
  "TRUE": "()", "FALSE": "()", "SWITCH": "({n};5;{n2};{n3})",
  # text
  "LEN": "({t1})", "LENB": "({t1})", "UPPER": "({t1})", "LOWER": "({t1})", "PROPER": "({t1})",
  "TRIM": "({t1})", "CLEAN": "({t1})", "LEFT": "({t1};{n2})", "LEFTB": "({t1};{n2})",
  "RIGHT": "({t1};{n2})", "RIGHTB": "({t1};{n2})", "MID": "({t1};{n2};{n3})", "MIDB": "({t1};{n2};{n3})",
  "REPLACE": "({t1};{n2};{n3};{t2})", "SUBSTITUTE": "({csv};\",\";\";\")", "REPT": "({t2};{n3})",
  "CONCATENATE": "({t1};{t2})", "CONCAT": "({t1};{t2})", "TEXTJOIN": "(\",\";1;{tr})",
  "FIND": "(\"е\";{t1})", "FINDB": "(\"е\";{t1})", "SEARCH": "(\"е\";{t1})", "SEARCHB": "(\"е\";{t1})",
  "EXACT": "({t1};{t1})", "T": "({t1})", "VALUE": "({tnum})", "NUMBERVALUE": "({tnum})",
  "TEXT": "({hun};\"0.00\")", "FIXED": "({rate};{n2})", "DOLLAR": "({hun})", "BAHTTEXT": "({hun})",
  "CHAR": "(65)", "UNICHAR": "(66)", "CODE": "({t1})", "UNICODE": "({t1})", "ASC": "({t1})",
  "JIS": "({t1})", "ROT13": "({t1})", "ROMAN2": "({ten})", "ENCODEURL": "({t1})",
  "WEBSERVICE": "(\"\")", "FILTERXML": "(\"<a/>\";\"//a\")", "REGEX": "({t1};\".\")",
  # date & time
  "DATE": "(2024;1;15)", "TIME": "(12;30;0)", "DATEVALUE": "(\"2024-01-15\")",
  "TIMEVALUE": "(\"12:30:00\")", "DAY": "({d1})", "MONTH": "({d1})", "YEAR": "({d1})",
  "HOUR": "({d1})", "MINUTE": "({d1})", "SECOND": "({d1})", "WEEKDAY": "({d1})",
  "WEEKNUM": "({d1})", "ISOWEEKNUM": "({d1})", "WEEKNUM_OOO": "({d1};1)", "DAYS": "({d2};{d1})",
  "DAYS360": "({d1};{d2})", "DAYSINMONTH": "({d1})", "DAYSINYEAR": "({d1})", "WEEKSINYEAR": "({d1})",
  "DATEDIF": "({d1};{d2};\"d\")", "EDATE": "({d1};{n2})", "EOMONTH": "({d1};{n2})",
  "NETWORKDAYS": "({d1};{d2})", "NETWORKDAYS.INTL": "({d1};{d2})", "WORKDAY": "({d1};{ten})",
  "WORKDAY.INTL": "({d1};{ten})", "YEARFRAC": "({d1};{d2})", "TODAY": "()", "NOW": "()",
  "EASTERSUNDAY": "(2024)", "ISLEAPYEAR": "({d1})", "MONTHS": "({d1};{d2};0)", "YEARS": "({d1};{d2};0)",
  "WEEKS": "({d1};{d2};0)", "ISOWEEKNUM_OOO": "({d1})",
  # lookup / spreadsheet
  "VLOOKUP": "({ten};{db};2)", "HLOOKUP": "(\"Цена\";{db};2;0)", "LOOKUP": "({ten};{r1})",
  "MATCH": "({six};{r1};0)", "INDEX": "({r1};{n3})", "OFFSET": "({cell};1;0)",
  "INDIRECT": "(\"BB1\")", "ADDRESS": "({n};{n2})", "ROW": "({cell})", "COLUMN": "({cell})",
  "ROWS": "({r1})", "COLUMNS": "({r1})", "AREAS": "({r1})", "CHOOSE": "({n2};{n};{n2};{n3})",
  "HYPERLINK": "(\"http://x\";\"x\")", "GETPIVOTDATA": "(\"\";{cell})", "FORMULA": "({cell})",
  "SHEET": "()", "SHEETS": "()", "XLOOKUP": "({ten};{r1};{r2})", "XMATCH": "({six};{r1})",
  "DDE": "(\"\";\"\";\"\")", "STYLE": "(\"Default\")", "CURRENT": "()",
  # information
  "ISBLANK": "({cell})", "ISNUMBER": "({n})", "ISTEXT": "({t1})", "ISNONTEXT": "({n})",
  "ISLOGICAL": "({b})", "ISERROR": "({n})", "ISERR": "({n})", "ISNA": "({n})",
  "ISREF": "({cell})", "ISFORMULA": "({cell})", "ISEVEN": "({ten})", "ISODD": "({n})",
  "N": "({n})", "NA": "()", "TYPE": "({n})", "ERROR.TYPE": "(1)", "CELL": "(\"row\";{cell})",
  "INFO": "(\"release\")", "ISODD_": "({n})", "CURRENT_": "()",
  # database
  "DSUM": "({db};2;{crit})", "DCOUNT": "({db};1;{crit})", "DCOUNTA": "({db};1;{crit})",
  "DAVERAGE": "({db};2;{crit})", "DMAX": "({db};2;{crit})", "DMIN": "({db};2;{crit})",
  "DPRODUCT": "({db};2;{crit})", "DGET": "({db};2;{crit})", "DSTDEV": "({db};2;{crit})",
  "DSTDEVP": "({db};2;{crit})", "DVAR": "({db};2;{crit})", "DVARP": "({db};2;{crit})",
  # array
  "MMULT": "({m1};{m2})", "MINVERSE": "({msq})", "MDETERM": "({msq})", "TRANSPOSE": "({r1})",
  "MUNIT": "({n2})", "SUMPRODUCT2": "({r1};{r2})", "FREQUENCY": "({r1};{r2})",
  "TREND": "({r1})", "GROWTH": "({r1})", "LINEST": "({r1})", "LOGEST": "({r1})",
  # statistical (common)
  "AVERAGE": "({r1})", "AVERAGEA": "({r1})", "MEDIAN": "({r1})", "MODE": "({r1})",
  "MODE.SNGL": "({r1})", "MAX": "({r1})", "MAXA": "({r1})", "MIN": "({r1})", "MINA": "({r1})",
  "COUNT": "({r1})", "COUNTA": "({r1})", "COUNTBLANK": "({r1})", "COUNTIF": "({r1};\">2\")",
  "COUNTIFS": "({r1};\">2\")", "AVERAGEIF": "({r1};\">2\")", "AVERAGEIFS": "({r1};{r1};\">2\")",
  "MAXIFS": "({r1};{r1};\">2\")", "MINIFS": "({r1};{r1};\">2\")",
  "STDEV": "({r1})", "STDEVA": "({r1})", "STDEVP": "({r1})", "STDEVPA": "({r1})",
  "STDEV.S": "({r1})", "STDEV.P": "({r1})", "VAR": "({r1})", "VARA": "({r1})", "VARP": "({r1})",
  "VARPA": "({r1})", "VAR.S": "({r1})", "VAR.P": "({r1})", "LARGE": "({r1};{n2})",
  "SMALL": "({r1};{n2})", "RANK": "({six};{r1})", "RANK.EQ": "({six};{r1})", "RANK.AVG": "({six};{r1})",
  "PERCENTILE": "({r1};{rate})", "PERCENTILE.INC": "({r1};{rate})", "PERCENTILE.EXC": "({r1};{rate})",
  "QUARTILE": "({r1};{n})", "QUARTILE.INC": "({r1};{n})", "QUARTILE.EXC": "({r1};{n})",
  "PERCENTRANK": "({r1};{six})", "PERCENTRANK.INC": "({r1};{six})", "PERCENTRANK.EXC": "({r1};{six})",
  "CORREL": "({r1};{r2})", "COVAR": "({r1};{r2})", "COVARIANCE.P": "({r1};{r2})",
  "COVARIANCE.S": "({r1};{r2})", "PEARSON": "({r1};{r2})", "RSQ": "({r1};{r2})",
  "SLOPE": "({r1};{r2})", "INTERCEPT": "({r1};{r2})", "STEYX": "({r1};{r2})",
  "FORECAST": "({six};{r1};{r2})", "FORECAST.LINEAR": "({six};{r1};{r2})",
  "TRIMMEAN": "({r1};{rate})", "GEOMEAN": "({r1})", "HARMEAN": "({r1})", "AVEDEV": "({r1})",
  "DEVSQ": "({r1})", "SKEW": "({r1})", "SKEWP": "({r1})", "KURT": "({r1})",
  "STANDARDIZE": "({six};{n2};{n})", "PROB": "({r1};{r2};0)", "COUNTA2": "({r1})",
  "NORMDIST": "({n};0;{n2};1)", "NORM.DIST": "({n};0;{n2};1)", "NORMSDIST": "({n})",
  "NORM.S.DIST": "({n};1)", "NORMINV": "({rate};0;{n2})", "NORM.INV": "({rate};0;{n2})",
  "NORMSINV": "({rate})", "NORM.S.INV": "({rate})", "GAUSS": "({n})", "PHI": "({n})",
  "CONFIDENCE": "({rate};{n2};{ten})", "CONFIDENCE.NORM": "({rate};{n2};{ten})",
  "CONFIDENCE.T": "({rate};{n2};{ten})", "BINOMDIST": "({n2};{ten};{rate};1)",
  "BINOM.DIST": "({n2};{ten};{rate};1)", "BINOM.INV": "({ten};{rate};{rate})",
  "CRITBINOM": "({ten};{rate};{rate})", "NEGBINOMDIST": "({n2};{n3};{rate})",
  "POISSON": "({n2};{n};1)", "POISSON.DIST": "({n2};{n};1)", "EXPONDIST": "({n};{n2};1)",
  "EXPON.DIST": "({n};{n2};1)", "HYPGEOMDIST": "({one};{n2};{n2};{ten})",
  "GAMMADIST": "({n};{n2};{n2};1)", "GAMMA.DIST": "({n};{n2};{n2};1)", "GAMMA": "({n})",
  "GAMMALN": "({n})", "GAMMALN.PRECISE": "({n})", "GAMMAINV": "({rate};{n2};{n2})",
  "GAMMA.INV": "({rate};{n2};{n2})", "BETADIST": "({rate};{n2};{n3})",
  "BETA.DIST": "({rate};{n2};{n3};1)", "BETAINV": "({rate};{n2};{n3})",
  "BETA.INV": "({rate};{n2};{n3})", "CHIDIST": "({n};{n2})", "CHISQDIST": "({n};{n2};1)",
  "CHISQ.DIST": "({n};{n2};1)", "CHISQ.DIST.RT": "({n};{n2})", "CHIINV": "({rate};{n2})",
  "CHISQINV": "({rate};{n2})", "CHISQ.INV": "({rate};{n2})", "CHISQ.INV.RT": "({rate};{n2})",
  "TDIST": "({n};{ten};1)", "T.DIST": "({n};{ten};1)", "T.DIST.2T": "({n};{ten})",
  "T.DIST.RT": "({n};{ten})", "TINV": "({rate};{ten})", "T.INV": "({rate};{ten})",
  "T.INV.2T": "({rate};{ten})", "FDIST": "({n};{six};{ten})", "F.DIST": "({n};{six};{ten};1)",
  "F.DIST.RT": "({n};{six};{ten})", "FINV": "({rate};{six};{ten})", "F.INV": "({rate};{six};{ten})",
  "F.INV.RT": "({rate};{six};{ten})", "FISHER": "({rate})", "FISHERINV": "({n})",
  "LOGNORMDIST": "({n};0;{n2})", "LOGNORM.DIST": "({n};0;{n2};1)", "LOGINV": "({rate};0;{n2})",
  "LOGNORM.INV": "({rate};0;{n2})", "WEIBULL": "({n};{n2};{n2};1)", "WEIBULL.DIST": "({n};{n2};{n2};1)",
  "ZTEST": "({r1};{six})", "Z.TEST": "({r1};{six})", "TTEST": "({r1};{r2};2;1)",
  "T.TEST": "({r1};{r2};2;1)", "FTEST": "({r1};{r2})", "F.TEST": "({r1};{r2})",
  "CHITEST": "({m1};{m2})", "CHISQ.TEST": "({m1};{m2})", "COUNTNUMS": "({r1})",
}

# ---- targeted arg fixes derived from the live error profile ----
SEEDS.update({"$AW$1": "2", "$AW$2": "2", "$AW$3": "3", "$AW$4": "4", "$AW$5": "5"})  # dup range for MODE
S["dup"] = "$AW$1:$AW$5"
SEEDS["$BA$19"] = ">30"  # DB criteria now matches exactly ONE row (Кол=40) so DGET returns a single value
OV.update({
    "PI": "()", "RAND": "()", "RAND.NV": "()", "RANDBETWEEN.NV": "({one};{ten})",
    "REPLACEB": "({t1};2;3;{t2})",
    "ERF.PRECISE": "({n})", "ERFC.PRECISE": "({n})",
    "MODE": "({dup})", "MODE.SNGL": "({dup})",
    "HYPGEOM.DIST": "({one};{n2};{n2};{ten};1)", "NEGBINOM.DIST": "({n2};{n3};{rate};1)",
    "PERCENTILE.EXC": "({r1};{half})",
    "QUARTILE": "({r1};1)", "QUARTILE.INC": "({r1};1)", "QUARTILE.EXC": "({r1};1)",
    "CEILING.XCL": "({ten};{n2})", "FLOOR.XCL": "({ten};{n2})",
    "ROUNDSIG": "({rate};{n2})", "FORMULA": "({d1})",
})

def build_arg(f):
    tmpl = OV.get(f["en"], CAT_DEF.get(f["cat"], "({n})"))
    try:
        return tmpl.format(**S)
    except Exception:
        return "({n})".format(**S)

# ---- convert an arg string's TOP-LEVEL ';' separators to ',' (xlsx canonical), keep quoted ';' ----
def to_comma(s):
    out = []; q = False
    for ch in s:
        if ch == '"':
            q = not q; out.append(ch)
        elif ch == ';' and not q:
            out.append(',')
        else:
            out.append(ch)
    return "".join(out)

# ---- lay out: category blocks side by side (name | English-formula), header row 1 ----
CAT_ORDER = ["FINANCIAL", "LOGICAL", "TEXT", "DATEnTIME", "STATISTICAL", "?", "SPREADSHEET",
             "INFORMATION", "DATABASE", "ARRAY"]
CAT_LABEL = {"FINANCIAL": "Финансовые", "LOGICAL": "Логические", "TEXT": "Текст",
             "DATEnTIME": "Дата и время", "STATISTICAL": "Статистические", "?": "Математические",
             "SPREADSHEET": "Ссылки и массивы", "INFORMATION": "Информация", "DATABASE": "База данных",
             "ARRAY": "Матричные"}
by_cat = {}
for f in funcs:
    by_cat.setdefault(f["cat"], []).append(f)

def colname(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26); s = chr(65 + r) + s
    return s

# The "Матричные" (ARRAY) functions AUTO-ARRAY-ENTER (Calc force-arrays matrix functions even on a plain
# Enter), so each spills DOWN several rows (e.g. FREQUENCY over 10 data + 10 bins spills 11 rows). Packed one
# row apart they overwrite the next function's cell → «нельзя изменить часть массива». Space THIS category
# out vertically so every spill lands in empty rows. ARRAY is the last category (rightmost cols), so its 2D
# spills (LINEST → col+1) fall into empty space too. Applied identically to the info grid and the UI plan.
def cat_stride(cat):
    return 20 if cat == "ARRAY" else 1

# grid: cellref (no $) -> ("num"|"str"|"formula", value). formula value has NO leading '='.
grid = {}
info = {}  # cellref -> {"name": display, "formula": ru-display-formula}  (for the error parser)
def seed_kind(v):
    if v.startswith("="):
        return ("formula", to_comma(v[1:]))
    if re.fullmatch(r"-?\d+", v):
        return ("num", v)
    return ("str", v)
for cell, v in SEEDS.items():
    grid[cell.replace("$", "")] = seed_kind(v)

c = 1
for cat in CAT_ORDER:
    fns = by_cat.get(cat, [])
    if not fns:
        continue
    ncol, fcol = colname(c), colname(c + 1)
    grid[f"{ncol}1"] = ("str", CAT_LABEL.get(cat, cat))
    row = 2
    for f in fns:
        args = to_comma(build_arg(f))
        grid[f"{ncol}{row}"] = ("str", f["ru"])          # localized name (text)
        grid[f"{fcol}{row}"] = ("formula", f["en"] + args)  # English formula (displays localized)
        info[f"{fcol}{row}"] = {"name": f["ru"], "formula": "=" + f["ru"] + build_arg(f)}
        row += cat_stride(cat)
    c += 2

# ---- write a minimal raw .xlsx (no deps) ----
def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def cell_xml(ref, kind, val):
    if kind == "num":
        return f'<c r="{ref}"><v>{val}</v></c>'
    if kind == "formula":
        return f'<c r="{ref}"><f>{xml_escape(val)}</f></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{xml_escape(val)}</t></is></c>'

rows = {}
for ref, (kind, val) in grid.items():
    m = re.match(r"([A-Z]+)(\d+)", ref); rows.setdefault(int(m.group(2)), []).append((m.group(1), ref, kind, val))
def col_key(cn):
    n = 0
    for ch in cn:
        n = n * 26 + (ord(ch) - 64)
    return n
sheet_rows = []
for r in sorted(rows):
    cs = sorted(rows[r], key=lambda x: col_key(x[0]))
    sheet_rows.append(f'<row r="{r}">' + "".join(cell_xml(ref, k, v) for _, ref, k, v in cs) + "</row>")
SHEET = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
         '<sheetData>' + "".join(sheet_rows) + '</sheetData></worksheet>')
WORKBOOK = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Функции" sheetId="1" r:id="rId1"/></sheets></workbook>')
WB_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
           '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
      '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
import zipfile
with zipfile.ZipFile("/tmp/funcdoc.xlsx", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", CT)
    z.writestr("_rels/.rels", RELS)
    z.writestr("xl/workbook.xml", WORKBOOK)
    z.writestr("xl/_rels/workbook.xml.rels", WB_RELS)
    z.writestr("xl/worksheets/sheet1.xml", SHEET)

json.dump({"info": info}, open("/tmp/funcdoc.json", "w"), ensure_ascii=False)
print("functions:", len(funcs), "| formula cells:", len(info), "| grid cells:", len(grid), "| wrote /tmp/funcdoc.xlsx")

# ---- ALSO emit a UI-INSERTION plan for the Playwright build (ribbon menu + wizard) ----
# Seeds are TYPED as values with LOCALIZED function names; formulas are INSERTED via the UI.
def ru_seed(v):
    if v.startswith("="):
        body = v[1:].replace("DATE", "ДАТА").replace("TRUE", "ИСТИНА").replace("FALSE", "ЛОЖЬ")
        return "=" + body
    return v
seeds_typed = [{"cell": k.replace("$", ""), "text": ru_seed(v)} for k, v in SEEDS.items()]

CAT_BTN = {
    "FINANCIAL": ["Formula-FinancialFunctions"],
    "LOGICAL": ["Formula-LogicalFunctions"],
    "TEXT": ["Formula-TextFunctions"],
    "DATEnTIME": ["Formula-DateAndTimeFunctions"],
    "SPREADSHEET": ["Formula-LookupAndRefFunctions"],
    "?": ["Formula-MathAndTrigFunctions"],
    "STATISTICAL": ["Formula-MoreFunctions"],
    "INFORMATION": ["Formula-MoreFunctions"],
    "DATABASE": ["Formula-MoreFunctions"],
    "ARRAY": ["Formula-MoreFunctions"],
}
# each function's ACTUAL ribbon dropdown button comes from menu-map.json (dumped from the live UI),
# because the ribbon groups functions differently than the source category arrays.
try:
    menu_map = json.load(open(os.path.join(HERE, "menu-map.json")))["map"]
except Exception:
    menu_map = {}
blocks = []
c = 1
for cat in CAT_ORDER:
    fns = by_cat.get(cat, [])
    if not fns:
        continue
    ncol, fcol = colname(c), colname(c + 1)
    items = []
    row = 2
    for f in fns:
        inner = build_arg(f)[1:-1]  # args without the outer parens
        btn = menu_map.get(f["ru"], CAT_BTN[cat][0])
        items.append({"ru": f["ru"], "en": f["en"], "inner": inner, "btn": [btn],
                      "name_cell": f"{ncol}{row}", "f_cell": f"{fcol}{row}"})
        row += cat_stride(cat)
    blocks.append({"cat": cat, "label": CAT_LABEL.get(cat, cat), "btn": CAT_BTN[cat],
                   "name_col": ncol, "f_col": fcol, "header_cell": f"{ncol}1", "items": items})
    c += 2

import os
json.dump({"seeds": seeds_typed, "blocks": blocks}, open("/tmp/funcdoc-ui-plan.json", "w"), ensure_ascii=False)
print("ui-plan: seeds", len(seeds_typed), "| blocks", len(blocks), "| funcs",
      sum(len(b["items"]) for b in blocks), "-> /tmp/funcdoc-ui-plan.json")
