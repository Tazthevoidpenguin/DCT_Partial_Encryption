# 1. Phân tách công thức DCT 2D thành dạng 1D x 1D

Công thức toán học của DCT 2D (loại DCT-2 dùng trong chuẩn nén JPEG) cho một khối ảnh kích thước $8 \times 8$ được phát biểu như sau:

$$
F(u, v) = \alpha(u)\alpha(v) \sum_{x=0}^{7} \sum_{y=0}^{7} f(x, y) \cos \left( \frac{(2x + 1)u\pi}{16} \right) \cos \left( \frac{(2y + 1)v\pi}{16} \right)
$$

Trong đó:
- $f(x, y)$ là giá trị độ sáng pixel tại tọa độ $(x, y)$ trong khối ảnh $8 \times 8$ (sau khi đã trừ 128 để dịch tâm về 0).
- $F(u, v)$ là hệ số DCT tại tần số $(u, v)$ mà chúng ta cần tìm.
- $\alpha(u)$ và $\alpha(v)$ là các hệ số chuẩn hóa:

$$
\alpha(u) = 
\begin{cases} 
\sqrt{\frac{1}{8}} & \text{nếu } u = 0 \\ 
\sqrt{\frac{2}{8}} & \text{nếu } u > 0 
\end{cases}
$$

### Chứng minh tính khả tách (Separability):

Do các hàm số cosin trong công thức trên độc lập hoàn toàn theo từng biến (một hàm chỉ phụ thuộc vào tọa độ ngang $x$ và tần số $u$, hàm còn lại chỉ phụ thuộc vào tọa độ dọc $y$ và tần số $v$), ta có thể viết lại tổng hai chiều dưới dạng tích của hai tổng một chiều lồng nhau:

$$
F(u, v) = \sum_{x=0}^{7} \left[ \alpha(u) \cos \left( \frac{(2x + 1)u\pi}{16} \right) \cdot \left( \sum_{y=0}^{7} f(x, y) \cdot \alpha(v) \cos \left( \frac{(2y + 1)v\pi}{16} \right) \right) \right]
$$

Nếu chúng ta định nghĩa **Ma trận biến đổi DCT 1D** ký hiệu là $T$ kích thước $8 \times 8$, với mỗi phần tử tại dòng $u$ cột $x$ là:

$$
T(u, x) = \alpha(u) \cos \left( \frac{(2x + 1)u\pi}{16} \right)
$$

Thì công thức DCT 2D ở trên thu gọn lại thành:

$$
F(u, v) = \sum_{x=0}^{7} T(u, x) \left( \sum_{y=0}^{7} f(x, y) T(v, y) \right)
$$
