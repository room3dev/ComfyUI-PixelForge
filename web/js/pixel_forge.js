import { app } from "/scripts/app.js";

// PixelForge Resolution Matrix - Frontend Extension
console.log("PixelForge: Extension script loaded");

app.registerExtension({
    name: "PixelForge.ResolutionMatrix",

    async nodeCreated(node) {
        console.log("PixelForge: nodeCreated called for", node.comfyClass);

        if (node.comfyClass !== "PixelForge") return;

        console.log("PixelForge: Initializing PixelForge node");

        const ASPECT_RATIOS = {
            "1:1": [1, 1],
            "3:2": [3, 2],
            "4:3": [4, 3],
            "16:9": [16, 9],
            "16:10": [16, 10],
        };

        const MP_BASE = 1024 * 1024;

        const aspectWidget = node.widgets.find(w => w.name === "aspect_ratio");
        const orientationWidget = node.widgets.find(w => w.name === "orientation");
        const divisibleWidget = node.widgets.find(w => w.name === "divisible_by");
        const mpLimitWidget = node.widgets.find(w => w.name === "max_megapixels");
        const resolutionWidget = node.widgets.find(w => w.name === "resolution");

        console.log("PixelForge: Found widgets:", {
            aspectWidget: !!aspectWidget,
            orientationWidget: !!orientationWidget,
            divisibleWidget: !!divisibleWidget,
            mpLimitWidget: !!mpLimitWidget,
            resolutionWidget: !!resolutionWidget
        });

        if (!aspectWidget || !resolutionWidget) {
            console.error("PixelForge: Required widgets not found!");
            return;
        }

        const updateResolutions = () => {
            const aspect = aspectWidget.value;
            const orientation = orientationWidget ? orientationWidget.value : "landscape";
            const div = divisibleWidget ? parseInt(divisibleWidget.value) : 16;
            const maxMpStr = mpLimitWidget ? mpLimitWidget.value : "4 MP";
            const maxMp = parseInt(maxMpStr.split(" ")[0]);

            console.log("PixelForge: updateResolutions called with:", { aspect, orientation, div, maxMp });

            const ratio = ASPECT_RATIOS[aspect];
            if (!ratio) {
                console.error("PixelForge: Invalid aspect ratio:", aspect);
                return;
            }

            const [ratio_w, ratio_h] = ratio;
            const maxPixels = maxMp * MP_BASE;

            const resolutions = [];
            let k = div;

            while (true) {
                let w = ratio_w * k;
                let h = ratio_h * k;
                const total = w * h;

                if (total > maxPixels) break;

                if (orientation === "portrait") {
                    [w, h] = [h, w];
                }

                resolutions.push(`${w}×${h}`);
                k += div;
            }

            if (resolutions.length === 0) {
                resolutions.push("INVALID");
            }

            console.log("PixelForge: Generated resolutions:", resolutions.length, resolutions.slice(0, 5));

            // Update the widget options
            resolutionWidget.options.values = resolutions;

            // If current value is not in the new list, pick the first one
            if (!resolutions.includes(resolutionWidget.value)) {
                console.log("PixelForge: Current value not in list, setting to:", resolutions[0]);
                resolutionWidget.value = resolutions[0];
            }

            node.setDirtyCanvas(true, true);
            console.log("PixelForge: Canvas marked dirty");
        };

        // Hook callbacks for all triggers
        const widgetsToWatch = [aspectWidget, orientationWidget, divisibleWidget, mpLimitWidget];
        widgetsToWatch.forEach(widget => {
            if (!widget) return;
            const origCallback = widget.callback;
            widget.callback = function () {
                console.log("PixelForge: Widget callback triggered for:", widget.name);
                const result = origCallback ? origCallback.apply(this, arguments) : undefined;
                updateResolutions();
                return result;
            };
        });

        console.log("PixelForge: Callbacks hooked, running initial update");

        // Initial update
        setTimeout(() => updateResolutions(), 10);
    },

    async loadedGraphNode(node) {
        if (node.comfyClass !== "PixelForge") return;

        console.log("PixelForge: loadedGraphNode called");

        // Re-trigger the same logic when a node is loaded
        const aspectWidget = node.widgets.find(w => w.name === "aspect_ratio");
        if (aspectWidget && aspectWidget.callback) {
            aspectWidget.callback();
        }
    }
});

console.log("PixelForge: Extension registered");
