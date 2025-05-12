import requests
import os
import time

# --- 設定項目 ---
# APIのベースURL 
BASE_API_URL = "https://zukan.pokemon.co.jp/zukan-api/api/search/"

# 取得したい画像のタイプ ('image_s': 小さい画像, 'image_m': 少し大きい画像)
IMAGE_KEY = 'image_s'

# 画像を保存するフォルダ名
SAVE_DIRECTORY = "pokemon_images"

# 各リクエスト間の待機時間 (秒) - サーバー負荷軽減のため
API_REQUEST_DELAY = 0.5  # APIへのリクエスト間の遅延
IMAGE_DOWNLOAD_DELAY = 0.1 # 画像ダウンロード間の遅延
# --- 設定項目ここまで ---

all_image_urls = []
pokemon_per_page = 64 # APIの1ページあたりのデフォルトアイテム数 (JSONレスポンスで確認したもの)
total_pages = 0

# --- ステップ1: APIから全ての画像URLを取得 ---
print("--- ステップ1: 画像URLの取得開始 ---")

# まず最初のページを取得して総ページ数を確認
try:
    print(f"ページ 1 を取得中 (総ページ数確認のため)...")
    params = {
        'limit': pokemon_per_page,
        'page': 1
    }
    response = requests.get(BASE_API_URL, params=params, timeout=10)
    response.raise_for_status() # エラーがあればここで例外発生
    data = response.json()
    
    paging_info = data.get("paging", {})
    total_pages = paging_info.get("pageCount", 0)
    
    if total_pages == 0:
        print("エラー: APIレスポンスから総ページ数を特定できませんでした。")
        print(f"デバッグ情報 (paging): {paging_info}")
        exit() # 総ページ数が不明な場合は処理を中断
        
    print(f"総ページ数: {total_pages}")

    # 最初のページから画像URLを収集
    current_page_urls = []
    for pokemon in data.get("results", []):
        if IMAGE_KEY in pokemon and pokemon[IMAGE_KEY]:
            current_page_urls.append(pokemon[IMAGE_KEY])
    all_image_urls.extend(current_page_urls)
    print(f"ページ 1 から {len(current_page_urls)} 件の画像URLを取得しました。")
    
    # サーバーに負荷をかけすぎないよう、少し待機
    time.sleep(API_REQUEST_DELAY)

except requests.exceptions.RequestException as e:
    print(f"エラー: ページ 1 の取得に失敗しました。理由: {e}")
    exit() # 最初のページ取得失敗は致命的なので処理を中断
except ValueError: # JSONデコードエラー
    print(f"エラー: ページ 1 のJSONデータの解析に失敗しました。レスポンス内容 (先頭200文字): {response.text[:200]}...")
    exit()

# 2ページ目から残りのページを取得 (もし総ページ数が1より大きければ)
if total_pages > 1:
    for page_num in range(2, total_pages + 1):
        print(f"ページ {page_num}/{total_pages} を取得中...")
        params = {
            'limit': pokemon_per_page,
            'page': page_num
        }
        try:
            response = requests.get(BASE_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            current_page_urls = []
            for pokemon in data.get("results", []):
                if IMAGE_KEY in pokemon and pokemon[IMAGE_KEY]:
                    current_page_urls.append(pokemon[IMAGE_KEY])
            all_image_urls.extend(current_page_urls)
            print(f"ページ {page_num} から {len(current_page_urls)} 件の画像URLを取得しました。")
            
            time.sleep(API_REQUEST_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"エラー: ページ {page_num} の取得に失敗しました。理由: {e}")
            print("このページをスキップして次に進みます。")
            continue # エラーが発生したページはスキップ
        except ValueError:
            print(f"エラー: ページ {page_num} のJSONデータの解析に失敗しました。レスポンス内容 (先頭200文字): {response.text[:200]}...")
            print("このページをスキップして次に進みます。")
            continue

print(f"--- 画像URLの取得完了 ---")
print(f"合計 {len(all_image_urls)} 件の画像URLを取得しました。")


# --- ステップ2: 取得したURLから画像をダウンロードして保存 ---
if not all_image_urls:
    print("画像URLが取得できなかったため、ダウンロード処理をスキップします。")
else:
    print(f"\n--- ステップ2: {len(all_image_urls)} 個の画像のダウンロード開始 ---")
    
    # 保存先フォルダが存在しない場合は作成
    if not os.path.exists(SAVE_DIRECTORY):
        try:
            os.makedirs(SAVE_DIRECTORY)
            print(f"フォルダ '{SAVE_DIRECTORY}' を作成しました。")
        except OSError as e:
            print(f"エラー: フォルダ '{SAVE_DIRECTORY}' の作成に失敗しました。理由: {e}")
            print("ダウンロード処理を中断します。")
            exit() # フォルダ作成失敗は致命的

    successful_downloads = 0
    failed_downloads = 0
    
    for i, img_url in enumerate(all_image_urls):
        try:
            # 画像ファイル名を取得 (URLの最後の部分を利用)
            filename = img_url.split('/')[-1]
            if not filename: # URLが / で終わるなど、ファイル名が空になる場合を考慮
                filename = f"image_{i+1}.png" # デフォルトのファイル名

            save_path = os.path.join(SAVE_DIRECTORY, filename)
            
            # 既にファイルが存在する場合はスキップする (任意)
            # if os.path.exists(save_path):
            #     print(f"({i+1}/{len(all_image_urls)}) スキップ: {filename} は既に存在します。")
            #     successful_downloads +=1 # 既に存在するものも成功とカウントする場合
            #     continue

            print(f"({i+1}/{len(all_image_urls)}) ダウンロード中: {img_url} -> {save_path}")
            
            img_response = requests.get(img_url, stream=True, timeout=20) # 画像ダウンロードは少し長めにタイムアウト
            img_response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in img_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # print(f"保存しました: {save_path}") # 詳細表示したい場合
            successful_downloads += 1
            
            time.sleep(IMAGE_DOWNLOAD_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"エラー: {img_url} のダウンロードに失敗しました。理由: {e}")
            failed_downloads += 1
        except Exception as e:
            print(f"予期せぬエラー ({img_url}): {e}")
            failed_downloads += 1

    print("\n--- 画像のダウンロード処理完了 ---")
    print(f"成功: {successful_downloads} 件")
    print(f"失敗: {failed_downloads} 件")
    if failed_downloads > 0:
        print("一部の画像のダウンロードに失敗しました。エラーメッセージを確認してください。")