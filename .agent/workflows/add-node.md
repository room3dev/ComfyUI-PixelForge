---
description: how to add or update nodes in ComfyUI custom node
---

Follow these steps to add a new node or update existing ones in this repository.

### 1. Implementation Principles
- **Asynchronous I/O**: Use `ThreadPoolExecutor` for disk-heavy operations (saving/loading).
- **PyTorch Optimization**: Perform tensor normalization (`.float().div_(255.0)`) directly in PyTorch rather than NumPy to avoid memory overhead.
- **Visual Feedback**: Always include `comfy.utils.ProgressBar`.
- **Detailed Descriptions**: Include a `DESCRIPTION` class attribute for ComfyUI tooltips.

### 2. Adding a New Node
1. **Create Python File**: Create a new `.py` file for your node (e.g., `new_node_feature.py`).
2. **Implement Node Class**:
   - Ensure `CATEGORY = "CUSTOM_NODE_NAME"`.
   - Implement `DESCRIPTION`.
3. **Register in `__init__.py`**:
   - Import `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` from the new file.
   - Update the global mappings in `__init__.py`.
4. **Update Documentation**:
   - Add the new node details to `README.md` under the appropriate section.
5. **Security Check**:
   - For saving nodes, use `os.path.commonpath` to ensure the target directory is within the ComfyUI `output` folder.

### 3. Update Checklist
- [ ] Add `DESCRIPTION` to class.
- [ ] Use `ThreadPoolExecutor` if I/O bound.
- [ ] Update `README.md`.
- [ ] Register in `__init__.py`.