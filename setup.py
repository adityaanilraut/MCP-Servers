from setuptools import setup, find_packages

setup(
    name="url-scraper-mcp",
    version="0.1.0",
    description="An MCP server that scrapes URLs and returns structured content.",
    author="Aditya Raut",
    packages=find_packages(),
    py_modules=["url_scraper_mcp_fixed"],  # matches url-scraper-mcp-fixed.py
    install_requires=[
        "mcp[cli]>=0.1.0",
        "httpx>=0.27.0",
        "beautifulsoup4>=4.12.0",
        "anyio>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "url-scraper-mcp=url_scraper_mcp_fixed:__main__",  
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
