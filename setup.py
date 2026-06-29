from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="media-downloader-bot",
    version="1.0.0",
    author="MiMoCode",
    description="Telegram bot for downloading YouTube, Instagram, TikTok with format selection and Telegram optimization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/danialchoopan/telegram_bot_youtikinsta",
    packages=find_packages(),
    py_modules=["runBot"],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "media-bot=runBot:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Communications :: Chat",
    ],
)
