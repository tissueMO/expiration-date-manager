##############################################################################
#   汎用関数群
##############################################################################
import cv2
import numpy as np
import base64

def image_to_base64(numpy_image: np.ndarray) -> str:
    """NumPy配列をBase64形式の画像にエンコードします。

    Args:
        numpy_image (np.ndarray): NumPy配列の画像

    Returns:
        str: Base64形式の画像
    """
    _, data = cv2.imencode(".jpg", numpy_image)
    base64_image = base64.b64encode(data).decode(encoding="utf-8")
    return base64_image
