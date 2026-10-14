# The host runner only runs Docker; all compiled Linux binaries come from this
# conservative x86-64 userspace (AlmaLinux 8 / glibc 2.28).
FROM quay.io/pypa/manylinux_2_28_x86_64:2026.05.07-2

ARG PYTHON_VERSION=3.13.5
ARG PYTHON_SOURCE_SHA256=93e583f243454e6e9e4588ca2c2662206ad961659863277afcdb96801647d640

# The manylinux wheel-build interpreters need not include a shared libpython.
# PyInstaller requires it, so compile the same CPython patch tested on macOS.
RUN dnf install -y \
        openssl-devel zlib-devel bzip2-devel libffi-devel xz-devel \
        readline-devel sqlite-devel file fontconfig \
    && dnf clean all

RUN curl --fail --location --silent --show-error \
        "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz" \
        --output /tmp/oneline-python.tar.xz \
    && echo "${PYTHON_SOURCE_SHA256}  /tmp/oneline-python.tar.xz" | sha256sum --check - \
    && mkdir -p /tmp/oneline-python-src \
    && tar -xJf /tmp/oneline-python.tar.xz -C /tmp/oneline-python-src --strip-components=1 \
    && cd /tmp/oneline-python-src \
    && CFLAGS='-O2 -march=x86-64 -mtune=generic' \
       ./configure --prefix=/opt/oneline-python-3.13.5 --enable-shared \
       --without-static-libpython --with-ensurepip=install \
    && make -j2 \
    && make install \
    && rm -rf /tmp/oneline-python-src /tmp/oneline-python.tar.xz

ENV PATH=/opt/oneline-python-3.13.5/bin:$PATH
ENV LD_LIBRARY_PATH=/opt/oneline-python-3.13.5/lib
ENV PYTHONDONTWRITEBYTECODE=1

COPY packaging/linux/requirements-runtime.txt /tmp/oneline-requirements-runtime.txt
COPY packaging/linux/requirements-build.txt /tmp/oneline-requirements-build.txt
RUN sed -i 's#requirements-runtime.txt#/tmp/oneline-requirements-runtime.txt#' /tmp/oneline-requirements-build.txt \
    && python3.13 -m pip install --disable-pip-version-check \
       --only-binary=:all: --no-deps -r /tmp/oneline-requirements-build.txt \
    && python3.13 -m pip check \
    && python3.13 -c 'import sys; assert sys.version_info[:3] == (3, 13, 5)'

WORKDIR /workspace
