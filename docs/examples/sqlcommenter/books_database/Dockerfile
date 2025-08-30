FROM mysql:8.0

ENV MYSQL_ROOT_PASSWORD=root
ENV MYSQL_DATABASE=books
ENV MYSQL_USER=books
ENV MYSQL_PASSWORD=books123

ADD books.sql /docker-entrypoint-initdb.d/

# Prepare general logs
RUN mkdir -p /var/log && \
    touch /var/log/general.log && \
    chown mysql:mysql /var/log/general.log

EXPOSE 3306

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD mysqladmin ping -p${MYSQL_ROOT_PASSWORD} || exit 1

# Start MySQL with general logging enabled and compatible authentication
CMD ["mysqld", "--general-log=1", "--general-log-file=/var/log/general.log", "--default-authentication-plugin=mysql_native_password"]