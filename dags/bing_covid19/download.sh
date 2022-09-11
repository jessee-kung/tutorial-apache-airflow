SOURCE_PARQUET=https://pandemicdatalake.blob.core.windows.net/public/curated/covid-19/bing_covid-19_data/latest/bing_covid-19_data.parquet
TARGET_PARQUET=/opt/data/source/bing_covid-19_data.parquet
TARGET_PARQUET_TS=/opt/data/source/_last_update

LAST_MODIFIED=$(curl -sI $SOURCE_PARQUET | grep -i Last-Modified)
LATEST_TS=$(date -d "${LAST_MODIFIED//Last-Modified: /}" +"%s")
echo "latest file timestamp:" $LATEST_TS

CURRENT_TS=$([ -f "${TARGET_PARQUET_TS}" ] && cat ${TARGET_PARQUET_TS} || echo 0)
echo "current file timestamp:" $CURRENT_TS

if (( $LATEST_TS > $CURRENT_TS )); then
    echo "start update parquet file ... "
    curl -s $SOURCE_PARQUET --output $TARGET_PARQUET
    echo ${LATEST_TS} > $TARGET_PARQUET_TS
    echo "updated"
else
    echo "no need to update"
fi