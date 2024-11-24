import os
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from base64 import b64encode
import json
import time
import pandas as pd
import jieba
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib
from snownlp import SnowNLP
from pyecharts.charts import Map
from pyecharts import options as opts

matplotlib.rcParams["font.sans-serif"] = ["SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False


def encrypt_aes(text, key, iv):
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    padded_text = pad(text.encode("utf-8"), AES.block_size)
    ciphertext = cipher.encrypt(padded_text)
    return b64encode(ciphertext).decode("utf-8")


def b(a, b_key):
    c = b_key
    d = "0102030405060708"
    e = a
    f = encrypt_aes(e, c, d)
    return f


def fetch_comments(song_id, pageSize=2000):
    d = {
        "csrf_token": "a377fd1409c2d967e66527ddf3ce2c02",
        "cursor": "-1",
        "offset": "0",
        "orderType": "1",
        "pageNo": "1",
        "pageSize": f"{pageSize}",
        "rid": f"R_SO_4_{song_id}",
        "threadId": f"R_SO_4_{song_id}",
    }

    i = "BdQMOhNkLlEP6jc7"
    g = "0CoJUm6Qyw8W8jud"
    d_json = json.dumps(d)
    encText = b(d_json, g)
    encText = b(encText, i)

    encSecKey = "1cac8643f7b59dbd626afa11238b1a90fab1e08bc8dabeec8b649e8a121b63fc45c2bc3427c6a9c6e6993624ec2987a2547c294e73913142444ddeec052b6ec2f9a4bebf57784d250e08749f371d94b635159a1c6ebfda81ee40600f2a22a5c1e7f0903884e4b466024a8905f0074a9432fd79c24ccf6aff73ea36fd68153031"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    url = "https://music.163.com/weapi/comment/resource/comments/get?csrf_token="
    data = {"params": encText, "encSecKey": encSecKey}
    respond = requests.post(url, headers=headers, data=data).json()

    items = respond["data"]["comments"]
    comments_list = []
    for item in items:
        user_name = item["user"]["nickname"].replace(",", "，")
        user_city = item["ipLocation"]["location"]
        comment = item["content"].strip().replace("\n", "").replace(",", "，")
        praise = str(item["likedCount"])
        date = time.localtime(int(str(item["time"])[:10]))
        date = time.strftime("%Y-%m-%d %H:%M:%S", date)

        comments_list.append(
            {
                "user_name": user_name,
                "user_city": user_city,
                "comment": comment,
                "praise": praise,
                "date": date,
            }
        )

    df = pd.DataFrame(comments_list)
    df["sentiment"] = df["comment"].apply(lambda x: SnowNLP(x).sentiments)
    csv_path = os.path.join(result_dir, f"评论数据_{song_id}.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"评论已保存到 {csv_path}")

    return df


def load_stopwords(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        stopwords = set(line.strip() for line in f)
    return stopwords


def generate_wordcloud(df, song_id):
    custom_stopwords = load_stopwords("./cn_stopwords.txt")
    all_comments = " ".join(df["comment"])
    words = " ".join(
        [word for word in jieba.cut(all_comments) if word not in custom_stopwords]
    )

    wordcloud = WordCloud(
        font_path="SimHei.ttf",
        width=800,
        height=400,
        background_color="white",
        stopwords=custom_stopwords,
        colormap="coolwarm",
    ).generate(words)

    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.title(f"歌曲 {song_id} 的评论词云", fontsize=16)
    img_path = os.path.join(result_dir, f"词云_{song_id}.png")
    plt.savefig(img_path)
    plt.show()

    print(f"词云已保存为 {img_path}")


def generate_sentiment_plot(df, song_id):

    positive_count = len(df[df["sentiment"] > 0.5])
    negative_count = len(df[df["sentiment"] <= 0.5])

    plt.figure(figsize=(8, 6))
    plt.bar(["negative", "positive"], [negative_count, positive_count], color="green")
    plt.title(f"歌曲 {song_id} 的情感分析结果", fontsize=16)
    plt.xlabel("情感分类")
    plt.ylabel("评论数量")
    img_path = os.path.join(result_dir, f"简易情感分析_{song_id}.png")
    plt.savefig(img_path)
    plt.show()

    print(f"情感分析图已保存为 {img_path}")


def generate_heatmap(df, song_id):
    city_counts = df["user_city"].value_counts().reset_index()
    city_counts.columns = ["city", "count"]

    city_alias = {
        "内蒙古": "内蒙古自治区",
        "广西": "广西壮族自治区",
        "宁夏": "宁夏回族自治区",
        "西藏": "西藏自治区",
        "新疆": "新疆维吾尔自治区",
        "香港": "香港特别行政区",
        "澳门": "澳门特别行政区",
        "台湾": "台湾省",
    }

    city_counts["city"] = city_counts["city"].replace(city_alias)

    map_chart = (
        Map()
        .add(
            "评论数",
            [list(z) for z in zip(city_counts["city"], city_counts["count"])],
            "china",
            is_map_symbol_show=False,
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title=f"歌曲 {song_id} 的评论地域分布"),
            visualmap_opts=opts.VisualMapOpts(max_=city_counts["count"].max()),
        )
    )

    html_path = os.path.join(result_dir, f"热力图_{song_id}.html")
    map_chart.render(html_path)
    print(f"地域热力图已保存为 {html_path}")


def generate_time_series_plot(df, song_id):

    df["date_only"] = pd.to_datetime(df["date"]).dt.date
    date_counts = df["date_only"].value_counts().sort_index()

    plt.figure(figsize=(12, 6))
    plt.plot(
        date_counts.index, date_counts.values, marker="o", linestyle="-", color="blue"
    )
    plt.title(f"歌曲 {song_id} 的每日评论数", fontsize=16)
    plt.xlabel("日期")
    plt.ylabel("评论数量")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.grid(True)
    img_path = os.path.join(result_dir, f"每日评论_{song_id}.png")
    plt.savefig(img_path)
    plt.show()

    print(f"每日评论数折线图已保存为 {img_path}")


result_dir = "result"
if not os.path.exists(result_dir):
    os.makedirs(result_dir)

song_id = input("请输入歌曲ID：")
df = fetch_comments(song_id)
generate_wordcloud(df, song_id)
generate_sentiment_plot(df, song_id)
generate_heatmap(df, song_id)
generate_time_series_plot(df, song_id)
