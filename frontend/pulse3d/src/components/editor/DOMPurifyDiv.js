import DOMPurify from "dompurify";

export default function DOMPurifyDiv({ rawHTML }) {
  return (
    <div className="ql-editor">
      <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(rawHTML) }} />
    </div>
  );
}
