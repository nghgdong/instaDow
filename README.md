# instaDow

`instaDow` la mot CLI de tai post, reel va ca profile Instagram ve may tinh.

## Ho tro

- Public Instagram post URLs
- Public Instagram reel URLs
- Public Instagram profile URLs
- Instagram username targets nhu `nghgdong`
- Carousel posts
- Tuy chon luu caption, thumbnail, cookies cho media URLs va login/session cho profile downloads

## Cai dat

```powershell
python -m pip install -e .
```

Sau khi cai dat, ban co the dung lenh `instadow` truc tiep hoac chay `python -m instadow`.

## Cach dung

Tai mot post hoac reel:

```powershell
instadow https://www.instagram.com/reel/ABC123/
instadow https://www.instagram.com/p/POST_ID/
```

Tai mot profile bang link:

```powershell
instadow https://www.instagram.com/username/
```

Tai mot profile bang username:

```powershell
instadow username
```

Tai nhieu target cung luc:

```powershell
instadow `
  -o .\downloads `
  https://www.instagram.com/p/POST_ID/ `
  https://www.instagram.com/reel/REEL_ID/ `
  username
```

Gioi han so bai tai moi profile:

```powershell
instadow username --max-posts 20
```

Cap nhat profile va dung khi gap item da tai truoc do:

```powershell
instadow username --fast-update
```

Khong tai reels hoac avatar khi tai profile:

```powershell
instadow username --no-reels --no-profile-pic
```

Luu them caption va thumbnail:

```powershell
instadow --write-caption --write-thumbnail username
```

In metadata ma khong tai file:

```powershell
instadow --print-info username
instadow --print-info https://www.instagram.com/reel/REEL_ID/
```

Dung cookies da export neu media URL can dang nhap:

```powershell
instadow --cookies-file .\cookies.txt https://www.instagram.com/p/POST_ID/
```

Dang nhap de tai profile private hoac tang do on dinh khi tai profile:

```powershell
instadow username --login your_instagram_username
```

Neu muon dung session file rieng:

```powershell
instadow username --login your_instagram_username --session-file .\ig.session
```

## Ghi chu

- Media URL truc tiep duoc tai bang `yt-dlp`.
- Profile downloads duoc tai bang `instaloader`.
- Profile downloads co the yeu cau dang nhap, ngay ca voi mot so profile public, do thay doi rate-limit va co che truy cap cua Instagram.
- Lan dau dung `--login`, tool se thu nap session truoc. Neu chua co session, no se hoi mat khau tuong tac va luu session de dung lai sau do.
- Tool nay phu hop nhat voi noi dung cong khai hoac noi dung ban co quyen truy cap.
