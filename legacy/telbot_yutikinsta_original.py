import telebot
import os
import subprocess
from yt_dlp import YoutubeDL
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import string
import requests
import instaloader
import shutil




BOT_TOKEN = "API_KEY_TELEGRAM_BOT"
bot = telebot.TeleBot(BOT_TOKEN)
insta_load=instaloader.Instaloader()

allowed_chat_ids = [123456]
admin_chat_id=123456


quality_options = {
    "360p mp4": "360",
    "480p mp4": "480",
    "720p mp4": "720",
    "720p mkv": "720k",
    "1080p telegram": "1080t",
    "1080p mkv": "1080",
    "MP3 (Audio only)": "mp3"
}


def generate_random_string(length=10):
    letters = string.ascii_letters + string.digits 
    return ''.join(random.choice(letters) for _ in range(length))

def download_thumbnail(url):
    save_path=f"thumbnail_{generate_random_string(20)}.jpg"
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return save_path
    else:
        print("error thumnail")
        return None


def not_allowed_user_check(user_chat_id):
    if user_chat_id not in allowed_chat_ids:
        return True
    else:
        return False


def download_instagram_reel(message):
    url = message.text.strip()
    video_file=""
    try:
        post = instaloader.Post.from_shortcode(insta_load.context, url.split("/")[-2])
        if insta_load.download_post(post, target="insta"): 
            bot.send_message(message.chat.id, "ویدیو شما به موفقیت در سرور بارگیری شد")
        else:
            bot.send_message(message.chat.id, "مشکلی در بارگیری پیش آمده است لطفا دوباره تلاش کنید")
            
        video_files = [f for f in os.listdir(os.getcwd()+'/insta') if f.endswith('.mp4')]

        if not video_files:
            bot.reply_to(message, "ویدیو مورد نظر شما پیدا نشد لطفا یک لینک معتبر ارسال کنید")
            return
        
        video_file = os.getcwd()+'/insta/'+video_files[0] 
        print(video_file)
        with open(video_file, 'rb') as video:
            bot.send_video(message.chat.id, video)

    except Exception as e:
        bot.send_message(message.chat.id, "مشکلی پیش آمده است لطفا یک لینک معتبر ارسال کنید (اینستاگرام)")
    finally:
        if os.path.isdir(os.getcwd()+'/insta'):
            shutil.rmtree(os.getcwd()+'/insta') 
        
@bot.message_handler(commands=['addallow'])
def add_allowed_user(message):
    if message.chat.id != admin_chat_id:
        bot.send_message(message.chat.id, "sorry the bot is not avaiable ")
        
        return

    try:
        new_chat_id = int(message.text.split()[1])
        if new_chat_id not in allowed_chat_ids:
            allowed_chat_ids.append(new_chat_id)        
            bot.send_message(message.chat.id, f"Chat ID {new_chat_id} با موفقیت به لیست کاربرهای مجاز اضافه شد ") 
        else:
            bot.send_message(message.chat.id, f"Chat ID {new_chat_id} قبلا به لیست اضافه شده است")
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "خطایی پیش آمده است لطفا دوباره امتحان کنید \n Usage: /addallow [chat_id]")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not_allowed_user_check(message.chat.id):
        bot.send_message(message.chat.id, f"sorry the bot is not avaiable \n your chat id {message.chat.id} ")
        return

    bot.send_message(
        message.chat.id,
        "سلام به یوتیوب چان خوش آمدی من لینک یوتیوب ازت میگیرم فایل شو برات میفرستم."
    )
    

@bot.message_handler(func=lambda message: message.text.startswith("http"))
def ask_quality(message):
    if not_allowed_user_check(message.chat.id):
        bot.send_message(message.chat.id, "sorry the bot is not avaiable ")
        return
    try:
        url = message.text
        markup = InlineKeyboardMarkup()
        for label, res in quality_options.items():
            markup.add(InlineKeyboardButton(label, callback_data=f"{url}|{res}"))
        bot.send_message(message.chat.id, "کیفیت مورد نظر خود را انتخاب کنید (480dp بهترین سرعت)", reply_markup=markup)
    except:
        try:
            download_instagram_reel(message)
        except:
            bot.send_message(message.chat.id, "مشکلی پیش آمده است لطفا یک لینک معتبر ارسال کنید (یوتیوب ، تیک تاک، اینستاگرام)")



@bot.callback_query_handler(func=lambda call: True)
def download_video(call):
    url, quality = call.data.split("|")
    chat_id = call.message.chat.id
    bot.send_message(chat_id, f"شروع بارگیری فایل در سرور \n {quality}")

    if quality == "mp3":
        ydl_opts = {
            'format': 'bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'downloaded_file_{generate_random_string()}'+'.%(ext)s'
        }
    elif quality=="720k":
        ydl_opts = {
            'format': f"bestvideo[height<=720]+bestaudio/best[height<=720]",
            'merge_output_format': 'mkv',
            'outtmpl': f'downloaded_file_{generate_random_string()}'+'.%(ext)s'
        }
    elif quality=="1080":        
        ydl_opts = {
            'format': f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
            'merge_output_format': 'mkv',
            'outtmpl': f'downloaded_file_{generate_random_string()}'+'.%(ext)s'
        }
    
    elif quality=="1080t":        
        ydl_opts = {
            'format': f"bestvideo[height<=1080]+bestaudio/best",
            'merge_output_format': 'mp4',
            'outtmpl': f'downloaded_file_{generate_random_string()}'+'.%(ext)s'
        }
    else:
        ydl_opts = {
            'format': f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
            'merge_output_format': 'mp4',
            'outtmpl': f'downloaded_file_{generate_random_string()}'+'.%(ext)s'
        }

    try:
        yudl_d=YoutubeDL(ydl_opts)
        yudl_d.download([url])
        
        you_info=yudl_d.extract_info(url, download=False)

        file_path = next((file for file in os.listdir() if file.startswith("downloaded_file_")), None)
        
        if file_path:
            bot.send_message(chat_id, "فایل درحال بارگذاری می باشد")
            with open(file_path, 'rb') as file:
                if quality=="mp3":
                    try:
                        path_to_thumnail=download_thumbnail(you_info.get("thumbnail",None))
                        cover_song_image=open(path_to_thumnail, 'rb')
                        bot.send_audio(chat_id,file,title=you_info.get('title',generate_random_string(20)),thumb=cover_song_image)
                        os.remove(path_to_thumnail)
                    except:
                        bot.send_audio(chat_id,file,title=you_info.get('title',generate_random_string(20)))
                        print('failded to download thumnail')
                elif quality=='1080':
                    bot.send_document(chat_id, file,caption=you_info.get('title',generate_random_string(20)))
                elif quality=='1080t':
                    bot.send_video(chat_id, file, caption=you_info.get('title', generate_random_string(20)))
                elif quality=='720k':
                    bot.send_document(chat_id, file,caption=you_info.get('title',generate_random_string(20)))
                else:
                    bot.send_document(chat_id, file,caption=you_info.get('title',generate_random_string(20)))
            os.remove(file_path)
        else:
            bot.send_message(chat_id, "مشکلی در دانلود فایل پیش آمده است لطفا دوباره تلاش کنید")
            try:
                os.remove(file_path)
            except:
                pass

    except Exception as e:
        try:
            file_path = next((file for file in os.listdir() if file.startswith("downloaded_file_")), None)
            os.remove(file_path)
        except:
            pass

        bot.send_message(chat_id, f"error : {str(e)}")


bot.polling()
