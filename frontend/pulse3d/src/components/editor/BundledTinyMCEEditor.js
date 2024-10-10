import { Editor } from "@tinymce/tinymce-react";

// TinyMCE so the global var exists
import "tinymce/tinymce";
// DOM model
import "tinymce/models/dom/model";
// Theme
import "tinymce/themes/silver";
// Toolbar icons
import "tinymce/icons/default";
// Editor styles
import "tinymce/skins/ui/oxide/skin";

// importing the plugin js.
// if you use a plugin that is not listed here the editor will fail to load
import "tinymce/plugins/advlist";
import "tinymce/plugins/anchor";
import "tinymce/plugins/autolink";
import "tinymce/plugins/autoresize";
import "tinymce/plugins/autosave";
import "tinymce/plugins/charmap";
import "tinymce/plugins/code";
import "tinymce/plugins/codesample";
import "tinymce/plugins/directionality";
import "tinymce/plugins/emoticons";
import "tinymce/plugins/fullscreen";
import "tinymce/plugins/help";
import "tinymce/plugins/help/js/i18n/keynav/en";
import "tinymce/plugins/image";
import "tinymce/plugins/importcss";
import "tinymce/plugins/insertdatetime";
import "tinymce/plugins/link";
import "tinymce/plugins/lists";
import "tinymce/plugins/media";
import "tinymce/plugins/nonbreaking";
import "tinymce/plugins/pagebreak";
import "tinymce/plugins/preview";
import "tinymce/plugins/quickbars";
import "tinymce/plugins/save";
import "tinymce/plugins/searchreplace";
import "tinymce/plugins/table";
import "tinymce/plugins/visualblocks";
import "tinymce/plugins/visualchars";
import "tinymce/plugins/wordcount";

// importing plugin resources
import "tinymce/plugins/emoticons/js/emojis";

// Content styles, including inline UI like fake cursors
import "tinymce/skins/content/default/content";
import "tinymce/skins/ui/oxide/content";

import DOMPurify from "dompurify";

export default function BundledTinyMCEEditor({ disabled = false, initialValue = "", ...props }) {
  const toolbar = disabled
    ? false
    : "blocks | " +
      "bold italic underline forecolor | " +
      "alignleft aligncenter alignright alignjustify | " +
      "bullist numlist outdent indent link";

  return (
    <Editor
      licenseKey="gpl"
      disabled={disabled}
      initialValue={DOMPurify.sanitize(initialValue)}
      init={{
        width: "80%",
        height: "60%",
        plugins: ["advlist", "autolink", "link", "lists"],
        toolbar: toolbar,
        menubar: false,
        statusbar: false,
        content_style: "body { font-family:Helvetica,Arial,sans-serif; font-size:14px }",
      }}
      {...props}
    />
  );
}
