'use client';

import type { HdlLanguage } from '@veridian/shared-types';
import Editor, { type Monaco } from '@monaco-editor/react';
import { useCallback } from 'react';

import { hdlLanguageToMonaco, registerMonacoLanguages } from '@/lib/monaco-languages';

export interface EditorSelectionState {
  startLine: number;
  endLine: number;
  startColumn: number;
  endColumn: number;
  text: string;
}

interface CodeEditorProps {
  value: string;
  language: HdlLanguage;
  path: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  onSelectionChange?: (selection: EditorSelectionState | null) => void;
  className?: string;
}

export function CodeEditor({
  value,
  language,
  path,
  onChange,
  onSave,
  onSelectionChange,
  className = '',
}: CodeEditorProps) {
  const handleMount = useCallback(
    (editor: Monaco['editor']['IStandaloneCodeEditor'], monaco: Monaco) => {
      registerMonacoLanguages(monaco);
      monaco.editor.setTheme('veridian-dark');

      editor.updateOptions({
        fontFamily: 'JetBrains Mono, Fira Code, Consolas, monospace',
        fontSize: 13,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: 'off',
        tabSize: 2,
        automaticLayout: true,
        padding: { top: 12, bottom: 12 },
      });

      if (onSave) {
        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
          onSave();
        });
      }

      if (onSelectionChange) {
        editor.onDidChangeCursorSelection(() => {
          const selection = editor.getSelection();
          const model = editor.getModel();
          if (!selection || !model) {
            onSelectionChange(null);
            return;
          }
          const text = model.getValueInRange(selection);
          if (!text.trim()) {
            onSelectionChange(null);
            return;
          }
          onSelectionChange({
            startLine: selection.startLineNumber,
            endLine: selection.endLineNumber,
            startColumn: selection.selectionStartColumn,
            endColumn: selection.selectionEndColumn,
            text,
          });
        });
      }
    },
    [onSave, onSelectionChange],
  );

  return (
    <div className={`flex min-h-0 flex-1 flex-col overflow-hidden ${className}`}>
      <Editor
        height="100%"
        path={path}
        language={hdlLanguageToMonaco(language)}
        value={value}
        theme="veridian-dark"
        beforeMount={registerMonacoLanguages}
        onMount={handleMount}
        onChange={(nextValue) => onChange(nextValue ?? '')}
        loading={
          <div className="flex h-full min-h-[200px] items-center justify-center bg-ide-bg text-sm text-ide-muted">
            Loading editor…
          </div>
        }
        options={{
          readOnly: false,
          renderWhitespace: 'selection',
          smoothScrolling: true,
          cursorBlinking: 'smooth',
          bracketPairColorization: { enabled: true },
          copyWithSyntaxHighlighting: false,
        }}
      />
    </div>
  );
}
