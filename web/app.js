const MAX_BYTES = 4 * 1024 * 1024;

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const fileList = document.getElementById("file-list");
const mergeBtn = document.getElementById("merge-btn");
const statusEl = document.getElementById("status");
const compressionEl = document.getElementById("compression");
const filenameEl = document.getElementById("filename");

/** @type {File[]} */
let files = [];

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function totalSize() {
  return files.reduce((sum, file) => sum + file.size, 0);
}

function setStatus(message, type = "") {
  statusEl.textContent = message;
  statusEl.className = type ? `status ${type}` : "status";
}

function renderList() {
  fileList.innerHTML = "";

  if (!files.length) {
    fileList.hidden = true;
    mergeBtn.disabled = true;
    return;
  }

  fileList.hidden = false;
  mergeBtn.disabled = false;

  files.forEach((file, index) => {
    const item = document.createElement("li");
    item.className = "file-item";

    item.innerHTML = `
      <span class="file-index">${index + 1}</span>
      <span class="file-name" title="${file.name}">${file.name} · ${formatSize(file.size)}</span>
      <div class="file-actions">
        <button type="button" class="icon-btn" data-action="up" ${index === 0 ? "disabled" : ""}>↑</button>
        <button type="button" class="icon-btn" data-action="down" ${index === files.length - 1 ? "disabled" : ""}>↓</button>
        <button type="button" class="icon-btn" data-action="remove">×</button>
      </div>
    `;

    item.querySelector('[data-action="up"]').addEventListener("click", () => {
      if (index === 0) return;
      [files[index - 1], files[index]] = [files[index], files[index - 1]];
      renderList();
    });

    item.querySelector('[data-action="down"]').addEventListener("click", () => {
      if (index === files.length - 1) return;
      [files[index + 1], files[index]] = [files[index], files[index + 1]];
      renderList();
    });

    item.querySelector('[data-action="remove"]').addEventListener("click", () => {
      files.splice(index, 1);
      renderList();
      setStatus("");
    });

    fileList.appendChild(item);
  });

  const total = totalSize();
  if (total > MAX_BYTES) {
    setStatus(`Total size ${formatSize(total)} exceeds the 4 MB limit.`, "error");
    mergeBtn.disabled = true;
  }
}

function addFiles(selected) {
  const pdfs = [...selected].filter((file) => file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf"));
  if (!pdfs.length) {
    setStatus("Only PDF files are allowed.", "error");
    return;
  }

  files.push(...pdfs);
  renderList();
  setStatus(`${files.length} file(s) ready.`, "success");
}

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});

fileInput.addEventListener("change", () => {
  if (fileInput.files?.length) addFiles(fileInput.files);
  fileInput.value = "";
});

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("active");
});

dropzone.addEventListener("dragleave", () => dropzone.classList.remove("active"));

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("active");
  if (event.dataTransfer?.files?.length) addFiles(event.dataTransfer.files);
});

mergeBtn.addEventListener("click", async () => {
  if (!files.length || totalSize() > MAX_BYTES) return;

  mergeBtn.disabled = true;
  setStatus("Merging…");

  const form = new FormData();
  files.forEach((file) => form.append("files", file, file.name));
  form.append("compression", compressionEl.value);
  form.append("filename", filenameEl.value.trim() || "merged.pdf");

  try {
    const response = await fetch("/api/merge", {
      method: "POST",
      body: form,
    });

    if (!response.ok) {
      let detail = "Could not merge PDFs.";
      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch {
        detail = await response.text() || detail;
      }
      throw new Error(detail);
    }

    const blob = await response.blob();
    const pages = response.headers.get("X-Page-Count");
    const downloadName = filenameEl.value.trim().endsWith(".pdf")
      ? filenameEl.value.trim()
      : `${filenameEl.value.trim() || "merged"}.pdf`;

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = downloadName;
    link.click();
    URL.revokeObjectURL(url);

    setStatus(pages ? `Done — ${pages} pages merged.` : "Done.", "success");
  } catch (error) {
    setStatus(error.message || "Something went wrong.", "error");
  } finally {
    mergeBtn.disabled = !files.length || totalSize() > MAX_BYTES;
  }
});
