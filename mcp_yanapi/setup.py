"""Setup untuk package mcp_yanapi_server.

Package ini menyediakan MCP server yang meng-export YanAPI functions sebagai tools.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="mcp-yanapi",
    version="0.1.0",
    author="Your Name",
    author_email="you@example.com",
    description="MCP server yang meng-export YanAPI functions sebagai tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "fastmcp",
        "mcp<2",
    ],
    entry_points={
        "console_scripts": [
            "mcp-yanapi = mcp_yanapi_server:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Public License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.5",
)