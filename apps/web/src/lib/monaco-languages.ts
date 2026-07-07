import type { HdlLanguage } from '@veridian/shared-types';
import type { Monaco } from '@monaco-editor/react';

let languagesRegistered = false;

const VERILOG_KEYWORDS = [
  'module',
  'endmodule',
  'input',
  'output',
  'inout',
  'wire',
  'reg',
  'logic',
  'always',
  'always_ff',
  'always_comb',
  'begin',
  'end',
  'assign',
  'initial',
  'if',
  'else',
  'case',
  'endcase',
  'posedge',
  'negedge',
  'parameter',
  'localparam',
  'generate',
  'endgenerate',
  'function',
  'endfunction',
  'task',
  'endtask',
  'posedge',
  'package',
  'endpackage',
  'import',
  'typedef',
  'enum',
  'struct',
  'interface',
  'endinterface',
  'class',
  'endclass',
];

const VHDL_KEYWORDS = [
  'entity',
  'architecture',
  'begin',
  'end',
  'process',
  'signal',
  'port',
  'is',
  'in',
  'out',
  'inout',
  'downto',
  'to',
  'library',
  'use',
  'all',
  'when',
  'others',
  'variable',
  'constant',
  'component',
  'generic',
  'map',
  'if',
  'then',
  'else',
  'elsif',
  'case',
  'when',
  'generate',
  'for',
  'loop',
  'while',
  'package',
  'body',
];

function keywordPattern(words: string[]): RegExp {
  return new RegExp(`\\b(${words.join('|')})\\b`);
}

function registerVerilogFamily(monaco: Monaco, languageId: string): void {
  monaco.languages.register({ id: languageId });
  monaco.languages.setMonarchTokensProvider(languageId, {
    defaultToken: '',
    ignoreCase: true,
    tokenizer: {
      root: [
        [keywordPattern(VERILOG_KEYWORDS), 'keyword'],
        [/\$[a-zA-Z_]\w*/, 'predefined'],
        [/\/\/.*$/, 'comment'],
        [/\/\*/, 'comment', '@blockComment'],
        [/"([^"\\]|\\.)*$/, 'string.invalid'],
        [/"/, 'string', '@string'],
        [/'[01xXzZ?]+/, 'number'],
        [/\d+'[bhdBHD][0-9a-fA-FxXzZ?]+/, 'number'],
        [/\d+/, 'number'],
        [/[{}()[\]]/, '@brackets'],
        [/[;,.]/, 'delimiter'],
      ],
      blockComment: [
        [/[^/*]+/, 'comment'],
        [/\*\//, 'comment', '@pop'],
        [/[/*]/, 'comment'],
      ],
      string: [
        [/[^\\"]+/, 'string'],
        [/\\./, 'string.escape'],
        [/"/, 'string', '@pop'],
      ],
    },
  });
}

function registerVhdl(monaco: Monaco): void {
  monaco.languages.register({ id: 'vhdl' });
  monaco.languages.setMonarchTokensProvider('vhdl', {
    defaultToken: '',
    ignoreCase: true,
    tokenizer: {
      root: [
        [keywordPattern(VHDL_KEYWORDS), 'keyword'],
        [/--.*$/, 'comment'],
        [/"([^"\\]|\\.)*$/, 'string.invalid'],
        [/"/, 'string', '@string'],
        [/'[^']*'/, 'string'],
        [/\d+#[0-9a-fA-F]+#/, 'number'],
        [/\d+/, 'number'],
        [/[;()]/, 'delimiter'],
      ],
      string: [
        [/[^\\"]+/, 'string'],
        [/\\./, 'string.escape'],
        [/"/, 'string', '@pop'],
      ],
    },
  });
}

export function registerMonacoLanguages(monaco: Monaco): void {
  if (languagesRegistered) return;
  languagesRegistered = true;

  registerVerilogFamily(monaco, 'verilog');
  registerVerilogFamily(monaco, 'systemverilog');
  registerVhdl(monaco);

  monaco.editor.defineTheme('veridian-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'keyword', foreground: '569cd6' },
      { token: 'predefined', foreground: 'dcdcaa' },
      { token: 'comment', foreground: '6a9955' },
      { token: 'string', foreground: 'ce9178' },
      { token: 'number', foreground: 'b5cea8' },
    ],
    colors: {
      'editor.background': '#1e1e1e',
      'editor.foreground': '#cccccc',
      'editorLineNumber.foreground': '#858585',
      'editorLineNumber.activeForeground': '#cccccc',
      'editor.selectionBackground': '#264f78',
      'editor.lineHighlightBackground': '#2a2d2e',
      'editorCursor.foreground': '#aeafad',
      'editorIndentGuide.background': '#404040',
    },
  });
}

export function hdlLanguageToMonaco(language: HdlLanguage): string {
  switch (language) {
    case 'verilog':
      return 'verilog';
    case 'systemverilog':
      return 'systemverilog';
    case 'vhdl':
      return 'vhdl';
    default:
      return 'plaintext';
  }
}
