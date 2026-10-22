% Halite FYP-I Mid Report class
% Professional layout derived from FAST-NUCES conventions (title page branding retained).
% Fixes: no blank even pages, tighter margins, title-only maketitle, restrained chapter heads.

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{halite-mid-report}[2026/10/18 Halite FYP Mid Report]

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{book}}
\ProcessOptions\relax
\LoadClass[11pt,a4paper,oneside,openany]{book}

\RequirePackage{amssymb,amsmath,amsthm,amstext}
\RequirePackage{tikz}
\RequirePackage{tocloft}
\RequirePackage[numbers,sort]{natbib}
\RequirePackage{graphicx}
\RequirePackage{fancyhdr}
\RequirePackage[english]{babel}
\RequirePackage{etoolbox}
\RequirePackage[perpage]{footmisc}
\RequirePackage{ifthen}
\RequirePackage{ifpdf}
\RequirePackage[utf8]{inputenc}
\RequirePackage[T1]{fontenc}
\RequirePackage{setspace}
\RequirePackage{enumitem}
\RequirePackage{booktabs}
\RequirePackage{longtable}
\RequirePackage{tabularx}
\RequirePackage{array}
\RequirePackage{caption}
\RequirePackage{float}
\RequirePackage{microtype}
\RequirePackage{url}
\RequirePackage{xurl}

% Research-paper style margins (not thesis-wide gutters)
\RequirePackage[
  left=2.0cm,
  right=2.0cm,
  top=2.0cm,
  bottom=2.2cm,
  includefoot,
  headheight=14pt
]{geometry}

% Full-width wrapping columns for tables
\newcolumntype{L}{>{\raggedright\arraybackslash}X}
\newcolumntype{C}{>{\centering\arraybackslash}X}
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.22}
\urlstyle{tt}
\Urlmuskip=0mu plus 2mu
% Prefer floats near their text; avoid orphan tiny tables on nearly empty pages
\setcounter{topnumber}{4}
\setcounter{bottomnumber}{4}
\setcounter{totalnumber}{6}
\renewcommand{\topfraction}{0.9}
\renewcommand{\bottomfraction}{0.9}
\renewcommand{\textfraction}{0.08}
\renewcommand{\floatpagefraction}{0.75}

\RequirePackage[
  bookmarks,
  bookmarksopen=true,
  bookmarksnumbered=true,
  breaklinks=true,
  linktocpage,
  colorlinks=true,
  linkcolor=black,
  urlcolor=black,
  citecolor=black,
  hyperindex=true
]{hyperref}

\renewcommand{\bibname}{References}

\setstretch{1.15}
\setlength{\parindent}{1.2em}
\setlength{\parskip}{0.35em}
\raggedbottom
\widowpenalty=300
\clubpenalty=300
\setcounter{secnumdepth}{3}
\setcounter{tocdepth}{2}
\pdfcompresslevel=9
\DeclareGraphicsExtensions{.png,.jpg,.jpeg,.pdf,.eps,.ps}

\captionsetup{
  font=small,
  labelfont=bf,
  skip=6pt,
  justification=centering
}

\setlist[itemize]{leftmargin=1.5em,itemsep=0.2em,topsep=0.35em,parsep=0pt}
\setlist[enumerate]{leftmargin=1.5em,itemsep=0.2em,topsep=0.35em,parsep=0pt}
\setlist[description]{leftmargin=4.2em,itemsep=0.15em,topsep=0.35em,parsep=0pt}

% Page style: clean headers, page number bottom-centre
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\footnotesize\itshape\leftmark}
\fancyhead[R]{\footnotesize\itshape\rightmark}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.3pt}
\renewcommand{\footrulewidth}{0pt}
\renewcommand{\chaptermark}[1]{\markboth{\thechapter.\ #1}{}}
\renewcommand{\sectionmark}[1]{\markright{\thesection\ #1}}

\fancypagestyle{plain}{%
  \fancyhf{}%
  \fancyfoot[C]{\thepage}%
  \renewcommand{\headrulewidth}{0pt}%
}

\fancypagestyle{frontmatter}{%
  \fancyhf{}%
  \fancyfoot[C]{\thepage}%
  \renewcommand{\headrulewidth}{0pt}%
}

% Compact chapter headings (professional, not sparse)
\renewcommand{\@makechapterhead}[1]{%
  \vspace*{12\p@}%
  {\parindent \z@ \raggedright \normalfont
    \ifnum \c@secnumdepth >\m@ne
      \large\bfseries\@chapapp\space\thechapter
      \par\nobreak
      \vskip 6\p@
    \fi
    \interlinepenalty\@M
    \LARGE\bfseries #1\par
    \nobreak
    \vskip 14\p@
  }}

\renewcommand{\@makeschapterhead}[1]{%
  \vspace*{12\p@}%
  {\parindent \z@ \raggedright
    \normalfont
    \interlinepenalty\@M
    \LARGE\bfseries #1\par
    \nobreak
    \vskip 14\p@
  }}

% Chapter always starts on a fresh page; oneside+openany => no blank filler pages
\newcommand{\HaliteChapterClear}{\clearpage}
\let\HaliteOrigChapter\chapter
\renewcommand{\chapter}{\HaliteChapterClear\HaliteOrigChapter}

% Metadata commands (FAST-compatible)
\def\degreeyear#1{\gdef\@degreeyear{#1}}
\def\degreemonth#1{\gdef\@degreemonth{#1}}
\def\department#1{\gdef\@department{#1}}
\def\faculty#1{\gdef\@faculty{#1}}
\def\supervisor#1{\gdef\@supervisor{#1}}
\def\cosupervisor#1{\gdef\@cosupervisor{#1}}
\def\sessionduration#1{\gdef\@sessionduration{#1}}
\def\degreename#1{\gdef\@degreename{#1}}
\def\campuscity#1{\gdef\@campuscity{#1}}
\def\authorone#1#2{\gdef\@authoronename{#1}\gdef\@authoroneroll{#2}}
\def\authortwo#1#2{\gdef\@authortwoname{#1}\gdef\@authortworoll{#2}}
\def\authorthree#1#2{\gdef\@authorthreename{#1}\gdef\@authorthreeroll{#2}}
\def\authorfour#1#2{\gdef\@authorfourname{#1}\gdef\@authorfourroll{#2}}

% Title page only (no auto TOC — that caused duplication in the stock class)
\renewcommand{\maketitle}{%
  \begin{titlepage}
    \thispagestyle{empty}
    \centering
    \vspace*{0.4cm}
    {\fontsize{20}{24}\selectfont\bfseries\@title\par}
    \vspace{1.0cm}
    {\large Project Team\par}
    \vspace{0.45cm}
    {\large
    \begin{tabular}{@{}ll@{}}
      \@authoronename & \@authoroneroll \\[0.3em]
      \@authortwoname & \@authortworoll \\[0.3em]
      \@authorthreename & \@authorthreeroll
    \end{tabular}\par}
    \vspace{0.7cm}
    {\large Session \@sessionduration\par}
    \vspace{0.8cm}
    {\large Supervised by\par}
    \vspace{0.25cm}
    {\Large\@supervisor\par}
    \vspace{1.0cm}
    % Logo alone on its own centred line (never beside department text)
    \includegraphics[width=3.4cm]{ThesisFigs/FASTLogo}\par
    \vspace{0.55cm}
    {\large\bfseries\@department\par}
    \vspace{0.35cm}
    {\large\bfseries National University of Computer and Emerging Sciences\\[0.2em]
    \@campuscity, Pakistan\par}
    \vspace{0.45cm}
    {\large\bfseries\@degreemonth, \@degreeyear\par}
    \vfill
    {\normalsize FYP-I Mid Report --- BS \@degreename\par}
  \end{titlepage}
}

% Breakable code / path text for long identifiers (\path from xurl)
\newcommand{\code}[1]{{\footnotesize\path{#1}}}

% Figure helper: diagrams keep aspect ratio, full text width
\newcommand{\HaliteFigure}[2]{%
  \begin{figure}[!htbp]
    \centering
    \includegraphics[width=\linewidth,height=0.72\textheight,keepaspectratio]{#1}%
    \caption{#2}%
  \end{figure}%
}

% Prefer native LaTeX tables; PDF clips only when unavoidable
\newcommand{\HaliteTableClip}[2]{%
  \begin{table}[!htbp]
    \centering
    \caption{#2}%
    \includegraphics[width=\linewidth,keepaspectratio]{#1}%
  \end{table}%
}
