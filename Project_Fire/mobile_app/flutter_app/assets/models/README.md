# 🔥 YOLO26 Fire Detection Model Setup

To get the AI detection working on your mobile app, follow these steps:

1.  **Download/Train your Model**: Ensure you have your trained fire detection model in `.pt` format (e.g., from Ultralytics YOLOv8/v11/YOLO26).
2.  **Convert to TFLite**: Use the following Python code to convert it for the Flutter app:
    ```python
    from ultralytics import YOLO
    model = YOLO("test.pt")
    model.export(format="tflite", imgsz=640)
    ```
3.  **Place the File**: Move the exported `test.tflite` file into this exact folder:
    `mobile_app/flutter_app/assets/models/test.tflite`
4.  **Verify names**: Ensure the file is named exactly `test.tflite` as set in `pubspec.yaml`.

Once placed, the app will automatically load the model on startup!
