'use client';

import type { HdlLanguage } from '@veridian/shared-types';
import Editor, { type Monaco } from '@monaco-editor/react';
import { useCallback } from 'react';

import { hdlLanguageToMonaco, registerMonacoLanguages } from '@/lib/monaco-languages';

interface CodeEditorProps {
  value: string;
  language: HdlLanguage;
  path: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  className?: string;
}

export function CodeEditor({ value, language, path, onChange, onSave, className = '' }: CodeEditorProps) {
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
    },
    [onSave],
  );

  return (
    <div className={`overflow-hidden rounded border border-ide-border ${className}`}>
      <Editor
        height="70vh"
        path={path}
        language={hdlLanguageToMonaco(language)}
        value={value}
        theme="veridian-dark"
        beforeMount={registerMonacoLanguages}
        onMount={handleMount}
        onChange={(nextValue) => onChange(nextValue ?? '')}
        loading={
          <div className="flex h-[70vh] items-center justify-center bg-ide-bg text-sm text-ide-muted">
            Loading editor…
          </div>
        }
        options={{
          readOnly: false,
          renderWhitespace: 'selection',
          smoothScrolling: true,
          cursorBlinking: 'smooth',
          bracketPairColorization: { enabled: true },
        }}
      />
    </div>
  );
}
