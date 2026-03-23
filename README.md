# instaDow

`instaDow` la mot CLI nho gon de tai anh, video va reels tu Instagram ve may tinh.

## Ho tro

- Public Instagram post URLs
- Public Instagram reel URLs
- Carousel posts (se tai tung item trong bai viet)
- Tuy chon luu caption, thumbnail va su dung cookies file khi URL can dang nhap
- Chua ho tro profile URLs nhu `https://www.instagram.com/<username>/`

## Cai dat

```powershell
python -m pip install -e .
```

Sau khi cai dat, ban co the dung lenh `instadow` truc tiep hoac chay `python -m instadow`.

## Cach dung

Tai media vao thu muc `downloads/` mac dinh:

```powershell
instadow https://www.instagram.com/reel/ABC123/
```

Hoac:

```powershell
python -m instadow https://www.instagram.com/reel/ABC123/
```

Tai nhieu URL va chon thu muc dich:

```powershell
instadow `
  -o .\downloads `
  https://www.instagram.com/p/POST_ID/ `
  https://www.instagram.com/reel/REEL_ID/
```

Luu them caption va thumbnail:

```powershell
instadow --write-caption --write-thumbnail https://www.instagram.com/p/POST_ID/
```

In metadata ma khong tai file:

```powershell
instadow --print-info https://www.instagram.com/reel/REEL_ID/
```

Dung cookies da export neu URL can dang nhap:

```powershell
instadow --cookies-file .\cookies.txt https://www.instagram.com/p/POST_ID/
```

Neu dua vao link profile, tool se bao loi ngay va yeu cau dung link media cu the:

```powershell
instadow https://www.instagram.com/username/
```

## Ghi chu

- Tool nay phu hop nhat voi noi dung cong khai hoac noi dung ban co quyen truy cap.
- Instagram co the thay doi cach phan phoi media theo thoi gian. Neu gap loi, thu cap nhat `yt-dlp` bang `python -m pip install -U yt-dlp`.
- Neu URL yeu cau dang nhap, hay export cookies sang file `cookies.txt` theo dinh dang Netscape roi truyen vao qua `--cookies-file`.
