import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Veridian',
  description: 'The cloud IDE for HDL — develop FPGA projects entirely from your browser',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-ide-bg font-sans text-ide-text antialiased">
        {children}
      </body>
    </html>
  );
}
