import Editor from "./Editor";

export default function WrappedEditor({ editorRef, ...props }) {
  return <Editor {...props} ref={editorRef} />;
}
