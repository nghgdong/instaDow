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

Chi tai reels tu profile:

```powershell
instadow username --reels-only --cookies-file .\instagram_cookies.txt
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

Dung cookies da export neu media URL hoac profile can dang nhap:

```powershell
instadow --cookies-file .\cookies.txt https://www.instagram.com/p/POST_ID/
instadow --cookies-file .\instagram_cookies.txt 11_14_42
```

Dang nhap de tai profile private hoac tang do on dinh khi tai profile:

```powershell
instadow username --login your_instagram_username
```

Sau khi login thanh cong mot lan, tool se nho session va tu dong thu nap lai o cac lan chay profile tiep theo. Luc do ban co the goi gon:

```powershell
instadow username
```

Neu muon dung session file rieng:

```powershell
instadow username --login your_instagram_username --session-file .\ig.session
```

## Ghi chu

- Media URL truc tiep duoc tai bang `yt-dlp`.
- Profile downloads duoc tai bang `instaloader`.
- `--cookies-file` ho tro file cookie Netscape va co the duoc dung cho ca media URLs lan profile downloads.
- Khi tai profile voi `--cookies-file`, tool uu tien goi Instagram profile feed API bang web session/cookies de on dinh hon GraphQL.
- `--reels-only` bo qua feed thuong va chi quet tab reels cua profile.
- Profile downloads co the yeu cau dang nhap, ngay ca voi mot so profile public, do thay doi rate-limit va co che truy cap cua Instagram.
- Lan dau dung `--login`, tool se thu nap session truoc. Neu chua co session, no se hoi mat khau tuong tac va luu session de dung lai sau do.
- Session login da luu se duoc nho lai trong cau hinh local cua user de nhung lan sau khong can truyen lai `--login`.
- Neu may chi co dung 1 session Instaloader da luu, tool cung se tu phat hien va thu dung session do.
- Tool nay phu hop nhat voi noi dung cong khai hoac noi dung ban co quyen truy cap.
