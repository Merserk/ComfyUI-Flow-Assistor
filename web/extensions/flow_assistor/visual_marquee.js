import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

app.registerExtension({
  name: "FlowAssistor.VisualMarquee",

  async setup() {
    api.addEventListener("flow_assistor_marquee_show", (event) => {
      const data = event.detail;
      if (!data || data.node_id == null) return;

      const graphId = Number(data.node_id);
      const node =
        app.graph.getNodeById(graphId) ||
        app.graph._nodes.find((n) => String(n.id) === String(data.node_id));

      if (!node) {
        console.warn("[VisualMarquee] Node not found for id:", data.node_id);
        return;
      }

      const imgInfo = { filename: data.filename, type: "temp", subfolder: "" };
      node.openMarqueeInterface(
        imgInfo,
        data.max_resolution,
        Boolean(data.original_size),
        String(data.node_id),
        String(data.token)
      );
    });
  },

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "VisualMarqueeSelection") return;

    nodeType.prototype.openMarqueeInterface = function (
      imgInfo,
      maxRes,
      originalSizeMode,
      nodeId,
      token
    ) {
      const elementId = `marquee_editor_${nodeId}`;
      let container = document.getElementById(elementId);

      if (!container) {
        container = document.createElement("div");
        container.id = elementId;
        Object.assign(container.style, {
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          backgroundColor: "#222",
          border: "1px solid #555",
          zIndex: "9000",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 0 50px rgba(0,0,0,0.9)",
          borderRadius: "8px",
          maxWidth: "92vw",
          maxHeight: "92vh",
        });
        document.body.appendChild(container);
      }

      const imageUrl = api.apiURL(
        `/view?filename=${encodeURIComponent(imgInfo.filename)}&type=${encodeURIComponent(
          imgInfo.type
        )}&subfolder=${encodeURIComponent(imgInfo.subfolder)}&t=${Date.now()}`
      );

      container.innerHTML = "";

      // Toolbar
      const toolbar = document.createElement("div");
      Object.assign(toolbar.style, {
        width: "100%",
        padding: "10px",
        background: "#333",
        display: "flex",
        justifyContent: "space-between",
        borderBottom: "1px solid #444",
        alignItems: "center",
        gap: "10px",
      });

      const statusWrap = document.createElement("div");
      Object.assign(statusWrap.style, { display: "flex", flexDirection: "column", gap: "2px" });

      const statusLabel = document.createElement("span");
      statusLabel.style.color = "#4caf50";
      statusLabel.style.fontWeight = "bold";
      statusLabel.innerText = "Select Area";
      statusWrap.appendChild(statusLabel);

      const modeLabel = document.createElement("span");
      modeLabel.style.color = "#bbb";
      modeLabel.style.fontSize = "12px";
      modeLabel.innerText = originalSizeMode
        ? "Mode: Original size (outputs exact selection)"
        : `Mode: Upscale to max_resolution (${maxRes}px)`;
      statusWrap.appendChild(modeLabel);

      toolbar.appendChild(statusWrap);

      const btnWrap = document.createElement("div");
      Object.assign(btnWrap.style, { display: "flex", gap: "8px", alignItems: "center" });

      const runBtn = document.createElement("button");
      runBtn.innerText = "CONFIRM & RESUME";
      Object.assign(runBtn.style, {
        backgroundColor: "#2196F3",
        color: "white",
        border: "none",
        padding: "8px 16px",
        borderRadius: "4px",
        cursor: "pointer",
        fontWeight: "bold",
        whiteSpace: "nowrap",
      });

      // Exit button (requested)
      const exitBtn = document.createElement("button");
      exitBtn.innerText = "✕";
      exitBtn.title = "Exit (cancels and stops the workflow)";
      Object.assign(exitBtn.style, {
        backgroundColor: "#444",
        color: "white",
        border: "1px solid #666",
        width: "32px",
        height: "32px",
        borderRadius: "6px",
        cursor: "pointer",
        fontWeight: "bold",
      });

      btnWrap.appendChild(runBtn);
      btnWrap.appendChild(exitBtn);
      toolbar.appendChild(btnWrap);

      container.appendChild(toolbar);

      // Canvas wrapper
      const canvasWrap = document.createElement("div");
      Object.assign(canvasWrap.style, {
        position: "relative",
        backgroundColor: "#111",
        cursor: "crosshair",
        overflow: "auto",
      });
      container.appendChild(canvasWrap);

      async function postPayload(payload) {
        // Try ComfyUI api route first, then direct.
        try {
          return await api.fetchApi("/flow_assistor/submit_crop", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
        } catch (e) {
          return await fetch("/flow_assistor/submit_crop", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
        }
      }

      const cleanup = (() => {
        const onKeyDown = (e) => {
          if (e.key === "Escape") {
            e.preventDefault();
            cancelAndClose();
          }
        };
        document.addEventListener("keydown", onKeyDown, { capture: true });

        return () => document.removeEventListener("keydown", onKeyDown, { capture: true });
      })();

      const cancelAndClose = async () => {
        runBtn.disabled = true;
        exitBtn.disabled = true;
        exitBtn.innerText = "...";
        try {
          const res = await postPayload({
            node_id: String(nodeId),
            token: String(token),
            action: "cancel",
          });
          if (!res || !res.ok) {
            const t = res ? await res.text() : "No response";
            console.error("[VisualMarquee] cancel failed:", res?.status, t);
          }
        } catch (err) {
          console.error("[VisualMarquee] cancel error:", err);
        } finally {
          cleanup();
          container.style.display = "none";
        }
      };

      exitBtn.onclick = cancelAndClose;

      const imgEl = new Image();
      imgEl.onload = function () {
        const maxDisplayW = Math.min(window.innerWidth * 0.85, 1200);
        const maxDisplayH = Math.min(window.innerHeight * 0.85, 900);

        const scale = Math.min(
          maxDisplayW / imgEl.naturalWidth,
          maxDisplayH / imgEl.naturalHeight,
          1.0
        );

        const displayW = imgEl.naturalWidth * scale;
        const displayH = imgEl.naturalHeight * scale;

        imgEl.style.width = `${displayW}px`;
        imgEl.style.height = `${displayH}px`;
        imgEl.style.display = "block";
        canvasWrap.appendChild(imgEl);

        // Selection box in REAL image coordinates
        let startSize = Math.min(512, imgEl.naturalWidth, imgEl.naturalHeight);
        let realBox = {
          x: Math.floor((imgEl.naturalWidth - startSize) / 2),
          y: Math.floor((imgEl.naturalHeight - startSize) / 2),
          w: startSize,
          h: startSize,
        };

        const box = document.createElement("div");
        Object.assign(box.style, {
          position: "absolute",
          border: "2px solid #00ff00",
          backgroundColor: "rgba(0, 255, 0, 0.15)",
          boxSizing: "border-box",
        });
        canvasWrap.appendChild(box);

        const handles = ["nw", "ne", "sw", "se"];
        const handleEls = {};
        handles.forEach((pos) => {
          const h = document.createElement("div");
          Object.assign(h.style, {
            position: "absolute",
            width: "12px",
            height: "12px",
            backgroundColor: "#fff",
            border: "1px solid #000",
            cursor: `${pos}-resize`,
            zIndex: "10",
          });
          box.appendChild(h);
          handleEls[pos] = h;
        });

        function clampBox() {
          if (realBox.w < 1) realBox.w = 1;
          if (realBox.h < 1) realBox.h = 1;
          if (realBox.x < 0) realBox.x = 0;
          if (realBox.y < 0) realBox.y = 0;

          if (realBox.w > imgEl.naturalWidth) realBox.w = imgEl.naturalWidth;
          if (realBox.h > imgEl.naturalHeight) realBox.h = imgEl.naturalHeight;

          if (realBox.x + realBox.w > imgEl.naturalWidth)
            realBox.x = imgEl.naturalWidth - realBox.w;
          if (realBox.y + realBox.h > imgEl.naturalHeight)
            realBox.y = imgEl.naturalHeight - realBox.h;
        }

        function updateUI() {
          const left = realBox.x * scale;
          const top = realBox.y * scale;
          const width = realBox.w * scale;
          const height = realBox.h * scale;

          box.style.left = `${left}px`;
          box.style.top = `${top}px`;
          box.style.width = `${width}px`;
          box.style.height = `${height}px`;

          const selW = Math.round(realBox.w);
          const selH = Math.round(realBox.h);
          statusLabel.innerText = `Selection: ${selW}x${selH}`;

          handleEls.nw.style.left = `-6px`; handleEls.nw.style.top = `-6px`;
          handleEls.ne.style.right = `-6px`; handleEls.ne.style.top = `-6px`;
          handleEls.sw.style.left = `-6px`; handleEls.sw.style.bottom = `-6px`;
          handleEls.se.style.right = `-6px`; handleEls.se.style.bottom = `-6px`;
        }

        let isDragging = false,
          isResizing = false,
          resizeDir = "",
          startX = 0,
          startY = 0,
          startBox = {};

        function onMouseDown(e) {
          e.preventDefault();
          e.stopPropagation();

          startX = e.clientX;
          startY = e.clientY;
          startBox = { ...realBox };

          if (e.target === box) {
            isDragging = true;
            box.style.cursor = "move";
          } else if (Object.values(handleEls).includes(e.target)) {
            isResizing = true;
            resizeDir = Object.keys(handleEls).find((k) => handleEls[k] === e.target);
          } else if (e.target === imgEl) {
            const rect = imgEl.getBoundingClientRect();
            realBox.x = (e.clientX - rect.left) / scale - realBox.w / 2;
            realBox.y = (e.clientY - rect.top) / scale - realBox.h / 2;
            clampBox();
            updateUI();
          }

          document.addEventListener("mousemove", onMouseMove);
          document.addEventListener("mouseup", onMouseUp);
        }

        function onMouseMove(e) {
          const dx = (e.clientX - startX) / scale;
          const dy = (e.clientY - startY) / scale;

          if (isDragging) {
            realBox.x = startBox.x + dx;
            realBox.y = startBox.y + dy;
          } else if (isResizing) {
            let newW = startBox.w;
            let newH = startBox.h;

            if (resizeDir.includes("e")) newW = startBox.w + dx;
            if (resizeDir.includes("s")) newH = startBox.h + dy;

            if (resizeDir.includes("w")) {
              realBox.x = startBox.x + dx;
              newW = startBox.w - dx;
            }
            if (resizeDir.includes("n")) {
              realBox.y = startBox.y + dy;
              newH = startBox.h - dy;
            }

            realBox.w = newW;
            realBox.h = newH;
          }

          clampBox();
          updateUI();
        }

        function onMouseUp() {
          isDragging = false;
          isResizing = false;
          box.style.cursor = "default";
          document.removeEventListener("mousemove", onMouseMove);
          document.removeEventListener("mouseup", onMouseUp);
        }

        canvasWrap.addEventListener("mousedown", onMouseDown);
        clampBox();
        updateUI();

        runBtn.onclick = async () => {
          runBtn.innerText = "Resuming...";
          runBtn.disabled = true;
          exitBtn.disabled = true;

          const payload = {
            node_id: String(nodeId),
            token: String(token),
            action: "submit",
            crop_data: {
              x: Math.round(realBox.x),
              y: Math.round(realBox.y),
              w: Math.round(realBox.w),
              h: Math.round(realBox.h),
            },
          };

          try {
            const res = await postPayload(payload);
            if (!res || !res.ok) {
              const text = res ? await res.text() : "No response";
              throw new Error(`Submit failed: ${res?.status} ${text}`);
            }
            container.style.display = "none";
          } catch (err) {
            console.error("[VisualMarquee] submit error:", err);
            runBtn.innerText = "Error (Check Console)";
            runBtn.disabled = false;
            exitBtn.disabled = false;
          } finally {
            cleanup();
          }
        };
      };

      imgEl.src = imageUrl;
      container.style.display = "flex";
    };
  },
});