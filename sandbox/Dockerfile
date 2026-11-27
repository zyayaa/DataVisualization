# Dockerfile
FROM python:3.15-slim

# Evitar ficheiros .pyc e buffers no stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Forçar backend headless no Matplotlib para não exigir ecrã (X11)
ENV MPLBACKEND=Agg

# Instalar dependências de análise e visualização
RUN pip install --no-cache-dir \
    pandas \
    seaborn \
    matplotlib \
    scipy \
    pyarrow \
    tabulate

# Criar utilizador não-root por segurança
RUN useradd -m -s /bin/bash sandboxuser

WORKDIR /workspace
RUN chown -R sandboxuser:sandboxuser /workspace

USER sandboxuser

# Manter o contentor vivo à espera de comandos do agente
CMD ["tail", "-f", "/dev/null"]
