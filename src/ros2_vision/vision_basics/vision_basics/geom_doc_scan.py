import cv2
import numpy as np


def order_points(pts):
    """将 4 个角点排序为：左上、右上、右下、左下"""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # 左上：x+y 最小
    rect[2] = pts[np.argmax(s)]  # 右下：x+y 最大
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # 右上：x-y 最小
    rect[3] = pts[np.argmax(diff)]  # 左下：x-y 最大
    return rect


def doc_scan(image):
    """自动文档扫描：边缘检测 → 找最大四边形 → 透视变换"""
    orig = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    # 形态学闭运算连接边缘
    kernel = np.ones((5, 5), np.uint8)
    edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    # 找最大四边形轮廓
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    doc_contour = None
    for c in contours[:5]:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            doc_contour = approx
            break

    if doc_contour is None:
        print("未找到文档轮廓")
        return None, None

    # 排序 4 个角点 + 计算透视变换
    rect = order_points(doc_contour.reshape(4, 2))
    (tl, tr, br, bl) = rect

    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxW = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxH = max(int(heightA), int(heightB))

    dst = np.float32([[0, 0], [maxW - 1, 0], [maxW - 1, maxH - 1], [0, maxH - 1]])
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(orig, M, (maxW, maxH))

    # 二值化增强
    warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(warped_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return warped, thresh


# === 生成合成"倾斜文档"作为测试 ===
doc = np.ones((500, 400, 3), dtype=np.uint8) * 240
# 模拟文字行
for i, y in enumerate(range(60, 440, 30)):
    cv2.putText(doc, f"Document Line {i + 1}", (50, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
cv2.rectangle(doc, (20, 20), (380, 480), (0, 0, 0), 2)  # 文档边框

# 用透视变换把"平"的文档变成"斜"的（模拟倾斜拍摄）
src_flat = np.float32([[0, 0], [400, 0], [400, 500], [0, 500]])
dst_tilt = np.float32([[50, 30], [430, 0], [380, 450], [20, 500]])
M_tilt = cv2.getPerspectiveTransform(src_flat, dst_tilt)
tilted = cv2.warpPerspective(doc, M_tilt, (500, 550))
# 加一点点噪声模拟真实拍摄
tilted = cv2.GaussianBlur(tilted, (3, 3), 1)

print("合成倾斜文档已生成，开始扫描...")
warped, thresh = doc_scan(tilted)

cv2.imshow('Tilted Document (input)', tilted)
cv2.imshow('Edge Detection', cv2.Canny(cv2.cvtColor(tilted, cv2.COLOR_BGR2GRAY), 75, 200))
if warped is not None:
    cv2.imshow('Corrected', warped)
    cv2.imshow('Thresholded', thresh)
cv2.waitKey(0)
cv2.destroyAllWindows()
