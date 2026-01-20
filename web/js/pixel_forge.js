import { app } from "../../../scripts/app.js";

// PixelForge Resolution Matrix - Frontend Extension
app.registerExtension({
    name: "PixelForge.ResolutionMatrix",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PixelForge") {
            const ASPECT_RATIOS = {
                "1:1": [1, 1],
                "3:2": [3, 2],
                "4:3": [4, 3],
                "16:9": [16, 9],
                "16:10": [16, 10],
            };

            const MP_BASE = 1024 * 1024;

            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                const aspectWidget = this.widgets.find(w => w.name === "aspect_ratio");
                const orientationWidget = this.widgets.find(w => w.name === "orientation");
                const divisibleWidget = this.widgets.find(w => w.name === "divisible_by");
                const mpLimitWidget = this.widgets.find(w => w.name === "max_megapixels");
                const resolutionWidget = this.widgets.find(w => w.name === "resolution");

                if (!resolutionWidget.options) resolutionWidget.options = { values: [] };

                const updateResolutions = () => {
                    const aspect = aspectWidget.value;
                    const orientation = orientationWidget.value;
                    const div = parseInt(divisibleWidget.value);
                    const maxMp = parseInt(mpLimitWidget.value.split(" ")[0]);

                    const ratio = ASPECT_RATIOS[aspect];
                    if (!ratio) return;

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

                    // Update the widget options
                    resolutionWidget.options.values = resolutions;

                    // If current value is not in the new list, pick the first one
                    if (!resolutions.includes(resolutionWidget.value)) {
                        resolutionWidget.value = resolutions[0];
                    }

                    if (this.setDirtyCanvas) {
                        this.setDirtyCanvas(true, true);
                    }
                };

                // Add callbacks to trigger update
                const widgetsToWatch = [aspectWidget, orientationWidget, divisibleWidget, mpLimitWidget];
                widgetsToWatch.forEach(widget => {
                    if (!widget) return;
                    const callback = widget.callback;
                    widget.callback = function () {
                        const result = callback ? callback.apply(this, arguments) : undefined;
                        updateResolutions();
                        return result;
                    };
                });

                // Initial update
                setTimeout(() => updateResolutions(), 10);

                return r;
            };

            // Ensure it updates when workflow is loaded
            nodeType.prototype.onConfigure = function () {
                setTimeout(() => {
                    const resolutionWidget = this.widgets.find(w => w.name === "resolution");
                    if (resolutionWidget && this.widgets.find(w => w.name === "aspect_ratio")) {
                        // Trigger update after a short delay to ensure all values are loaded
                        const updateResolutions = this.widgets.find(w => w.name === "aspect_ratio").callback;
                        if (updateResolutions) updateResolutions();
                    }
                }, 100);
            };
        }
    }
});
