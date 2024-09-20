import Quill from "quill";
import { forwardRef, useEffect, useRef } from "react";
import "quill/dist/quill.snow.css";

// Editor is an uncontrolled React component
// TODO make this component NOT server-side-rendered, so page refresh doesn't fail
const Editor = forwardRef(({ width = "80%", height = "50%" }, ref) => {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    const editorContainer = container.appendChild(container.ownerDocument.createElement("div"));

    const toolbar = [
      [{ header: [1, 2, 3, 4, 5, 6, false] }],
      ["bold", "italic", "underline", "strike"],
      ["blockquote", "code-block", "link"],
      [{ list: "ordered" }, { list: "bullet" }],
      [{ script: "sub" }, { script: "super" }],
      [{ indent: "-1" }, { indent: "+1" }, { align: [] }],
      [{ color: [] }, { background: [] }],
      ["clean"],
    ];

    const options = {
      modules: { toolbar },
      theme: "snow",
    };

    ref.current = new Quill(editorContainer, options);

    return () => {
      ref.current = null;
      container.innerHTML = "";
    };
  }, [ref]);

  return <div style={{ width, height }} ref={containerRef}></div>;
});

Editor.displayName = "Editor";

export default Editor;
