"""
Setup script for VibeSafe
"""
from setuptools import setup, find_packages
import platform
from pathlib import Path

# Base requirements
install_requires = [
    "cryptography>=41.0.0",
    "click>=8.1.0",
]

# Platform-specific requirements
extras_require = {
    "macos": [
        "pyobjc-core>=9.0",
        "pyobjc-framework-Security>=9.0",
        "pyobjc-framework-LocalAuthentication>=9.0",
        "pyobjc-framework-AuthenticationServices>=9.0",
        "pyobjc-framework-WebKit>=9.0",
    ],
    "fido2": [
        "fido2>=1.1.0",
    ],
    "dev": [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "black>=23.0.0",
        "flake8>=6.0.0",
    ],
}

# Add platform-specific deps automatically
if platform.system() == "Darwin":
    install_requires.extend(extras_require["macos"])

setup(
    name="vibesafe",
    version="1.0.0",
    author="VibeSafe Team",
    author_email="",
    maintainer="VibeSafe Contributors",
    description="Secure secrets manager with Touch ID/passkey protection for AI-assisted development",
    keywords="secrets, security, encryption, touch-id, biometric, keychain, claude, ai, api-keys, password-manager",
    long_description=Path("README.md").read_text(encoding="utf-8") if Path("README.md").exists() else "",
    long_description_content_type="text/markdown",
    url="https://github.com/1a-li-lu-le-lo/VibeSafe",
    project_urls={
        "Bug Reports": "https://github.com/1a-li-lu-le-lo/VibeSafe/issues",
        "Source": "https://github.com/1a-li-lu-le-lo/VibeSafe",
        "Documentation": "https://github.com/1a-li-lu-le-lo/VibeSafe#readme",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Security :: Cryptography",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "vibesafe=vibesafe.vibesafe:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)