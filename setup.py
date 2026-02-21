from setuptools import setup, find_packages

setup(
    name="sbas",
    version="0.1.0",
    description="Sequential Batch Agent System — run AI agents at 50% lower cost",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Lior Nataf & Matan Marudi",
    url="https://github.com/MrMarudi/SBAS",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[],
    extras_require={
        "redis": ["redis>=4.0"],
        "openai": ["openai>=1.0"],
        "anthropic": ["anthropic>=0.20"],
        "langchain": ["langchain>=0.1", "langchain-openai>=0.1"],
        "all": ["redis>=4.0", "openai>=1.0", "anthropic>=0.20", "langchain>=0.1"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
