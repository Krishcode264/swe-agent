import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ReportViewProps {
  markdown: string;
}

const ReportView: React.FC<ReportViewProps> = ({ markdown }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="text-3xl font-extrabold text-[#0a192f] border-b-2 border-slate-100 pb-4 mb-6 mt-8 first:mt-0 tracking-tight">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-xl font-bold text-[#0a192f] border-b border-slate-100 pb-3 mb-5 mt-8 tracking-tight">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-lg font-bold text-slate-800 mb-3 mt-6 tracking-tight">{children}</h3>
        ),
        p: ({ children }) => (
          <p className="text-slate-600 leading-relaxed mb-5 text-sm/6">{children}</p>
        ),
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noreferrer" className="font-semibold text-[#1e3a5f] hover:text-[#0a192f] underline underline-offset-4 decoration-slate-300 hover:decoration-[#0a192f] transition-all">{children}</a>
        ),
        ul: ({ children }) => (
          <ul className="list-disc list-outside ml-5 mb-6 space-y-2 text-sm/6 text-slate-600 marker:text-slate-400">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-outside ml-5 mb-6 space-y-2 text-sm/6 text-slate-600 marker:text-slate-400">{children}</ol>
        ),
        li: ({ children }) => <li className="leading-relaxed pl-1">{children}</li>,
        code: ({ className, children, ...props }) => {
          const isBlock = className?.includes('language-');
          return isBlock ? (
            <code className="block bg-[#0a192f] text-slate-100 text-[13px] font-mono p-5 rounded-xl overflow-x-auto mb-6 shadow-sm border border-black/10 whitespace-pre leading-snug" {...props}>
              {children}
            </code>
          ) : (
            <code className="bg-slate-100 text-[#0a192f] text-xs font-mono font-bold px-1.5 py-0.5 rounded-md border border-slate-200" {...props}>
              {children}
            </code>
          );
        },
        pre: ({ children }) => (
          <div className="relative group mb-6 rounded-xl overflow-hidden shadow-sm border border-slate-200 bg-[#0a192f]">
             <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
               {/* Decorative mac dots or similar styling could go here */}
             </div>
             <pre className="overflow-x-auto p-5 text-[13px] font-mono whitespace-pre text-slate-100">{children}</pre>
          </div>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-[#0a192f] pl-5 py-1 text-slate-600 italic mb-6 bg-slate-50/50 rounded-r-lg">{children}</blockquote>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto mb-6 rounded-xl border border-slate-200 shadow-sm bg-white">
            <table className="min-w-full text-sm border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-slate-50 border-b border-slate-200">{children}</thead>,
        th: ({ children }) => (
          <th className="border-b border-slate-200 px-5 py-3.5 text-left text-xs font-bold text-slate-500 uppercase tracking-widest">{children}</th>
        ),
        td: ({ children }) => (
          <td className="border-b border-slate-100 px-5 py-3.5 text-slate-700 font-medium text-sm">{children}</td>
        ),
        hr: () => <hr className="border-slate-200 my-8" />,
        strong: ({ children }) => <strong className="font-extrabold text-[#0a192f]">{children}</strong>,
      }}
    >
      {markdown}
    </ReactMarkdown>
  );
};

export default ReportView;
