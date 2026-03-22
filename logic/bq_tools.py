import streamlit as st
from google.cloud import bigquery
import pandas as pd
import json

PROJECT_ID = "din-homeindex-dev-irq"
client = bigquery.Client(project=PROJECT_ID, location="EU")

def get_criteria_details_characteristic(bu_id, prod_ref, code):
    """Pour les critères avec données dans le champ characteristic (ex: FRRR)"""
    query = f"""
    SELECT 
        char_item.characteristicName as att_name,
        char_item.characteristicName as att_id,
        char_item.characteristicValue as current_value,
        '{code}' as methodName
    FROM `din-homeindex-dev-irq.asfr_home_index_score_flow.v_homeIndexCriteriaData`,
    UNNEST(characteristic) as char_item
    WHERE productBuReference = {prod_ref}
    AND businessUnitIdentifier = {bu_id}
    AND criteriaCode = '{code}'
    LIMIT 10
    """
    return client.query(query).to_dataframe()

def get_full_product_data(bu_id, prod_ref):
    query = f"""
    WITH formatted_input AS (
      SELECT
        productDescriptiveModelIdentifier,
        supplierPurchaseSiteIdentifier,
        TO_JSON_STRING(JSON_STRIP_NULLS(JSON_OBJECT(
          'productBuReference', productBuReference,
          'businessUnitIdentifier', businessUnitIdentifier,
          'productDescriptiveModelIdentifier', productDescriptiveModelIdentifier,
          'supplierPurchaseSiteIdentifier', supplierPurchaseSiteIdentifier,
          'criteria', ARRAY_AGG(JSON_OBJECT(
            'criteriaCode', criteriaCode,
            'criteriaValue', CASE WHEN criteriaCode = 'EFCT' THEN criteriaValueIdentifier ELSE criteriaValue END,
            'criteriaValueIdentifier', CASE WHEN criteriaCode = 'EFCT' THEN criteriaValue ELSE criteriaValueIdentifier END,
            'proof', proof,
            'characteristic', characteristic
          ))
        ))) AS json_entry
      FROM `din-homeindex-dev-irq.asfr_home_index_score_flow.v_homeIndexCriteriaData`
      WHERE productBuReference = {prod_ref} AND businessUnitIdentifier = {bu_id}
      GROUP BY productBuReference, businessUnitIdentifier, productDescriptiveModelIdentifier, supplierPurchaseSiteIdentifier
    ),
    engine_call AS (
      SELECT 
        f.productDescriptiveModelIdentifier,
        f.supplierPurchaseSiteIdentifier,
        TO_JSON_STRING(`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine(PARSE_JSON(json_entry))) AS result_json
      FROM formatted_input f
    ),
    scores AS (
        SELECT
          JSON_VALUE(criterion, '$.criteriaCode') AS criteriaCode,
          SAFE_CAST(JSON_VALUE(criterion, '$.criteriaNote') AS FLOAT64) AS criteriaNote
        FROM engine_call,
        UNNEST(JSON_QUERY_ARRAY(result_json, '$[0].pillars')) AS pillar,
        UNNEST(JSON_QUERY_ARRAY(pillar, '$.criteria')) AS criterion
    ),
    all_criteria AS (
        SELECT DISTINCT criteriaCode
        FROM `din-homeindex-dev-irq.asfr_home_index_score_flow.v_homeIndexCriteriaData`
        WHERE productBuReference = {prod_ref} AND businessUnitIdentifier = {bu_id}
    ),
    catalogue AS (
        SELECT prod.*, art.itemPicture, art.itemName
        FROM `dfdp-data-foundation-prod.productDataFoundation.productCatalogue` prod
        INNER JOIN `din-homeindex-prd-08n.homeIndexPerformance.article` art
          ON art.businessUnitIdentifier = prod.businessUnitIdentifier
          AND art.itemIdentifier = prod.productBuReference
        WHERE prod.businessUnitIdentifier = {bu_id} AND prod.productBuReference = {prod_ref}
    )
    SELECT c.*, ac.criteriaCode, s.criteriaNote, e.productDescriptiveModelIdentifier, e.supplierPurchaseSiteIdentifier
    FROM catalogue c
    LEFT JOIN all_criteria ac ON 1=1
    LEFT JOIN scores s ON s.criteriaCode = ac.criteriaCode
    LEFT JOIN (SELECT DISTINCT productDescriptiveModelIdentifier, supplierPurchaseSiteIdentifier FROM engine_call) e ON 1=1
    """
    return client.query(query).to_dataframe()

@st.cache_data(ttl=3600)
def get_all_lovs():
    query = """
    SELECT DISTINCT hiCar.methodIdentifier as code, valCar.characteristicValue as label, valCar.characteristicValueCode as id
    FROM `dfdp-data-foundation-prod.productDataFoundation.characteristicModelLink` modCar
    INNER JOIN `dfdp-data-foundation-prod.productDataFoundation.characteristicValuesLink` valCar
      ON CONCAT('ATT_', valCar.characteristicIdentifier) = modCar.productDescriptiveCharacteristicIdentifier
    INNER JOIN `din-homeindex-dev-irq.homeIndex.homeIndexCharacteristic` hiCar
      ON hiCar.characteristicIdentifier = modCar.productDescriptiveCharacteristicIdentifier
    WHERE modCar.productDescriptiveCharacteristicName IS NOT NULL
    """
    return client.query(query).to_dataframe()

def get_criteria_details(bu_id, prod_ref, top_intl, code):
    query = f"""
    select prodCarVal.characteristicName as att_name
        , prodCarVal.characteristicIdentifier as att_id
        , prodCarVal.value as current_value
        , hiCar.methodName as methodName
    from `dfdp-data-foundation-prod.productDataFoundation.productCharacteristicsDenormalized` prodCarVal
    inner join `din-homeindex-dev-irq.homeIndex.homeIndexCharacteristic` hiCar
      on hiCar.characteristicIdentifier = prodCarVal.characteristicIdentifier
    where hiCar.methodIdentifier = '{code}'
    and prodCarVal.businessUnitIdentifier = {bu_id}
    and prodCarVal.productBuReference = {prod_ref}
    """
    return client.query(query).to_dataframe()

def get_criteria_details_simple(bu_id, prod_ref, code):
    query = f"""
    SELECT 
        criteriaCode as att_name,
        criteriaCode as att_id,
        COALESCE(criteriaValueIdentifier, criteriaValue) as current_value,
        criteriaValue as current_value_id,
        proof,
        criteriaCode as methodName
    FROM `din-homeindex-dev-irq.asfr_home_index_score_flow.v_homeIndexCriteriaData`
    WHERE productBuReference = {prod_ref}
    AND businessUnitIdentifier = {bu_id}
    AND criteriaCode = '{code}'
    LIMIT 1
    """
    return client.query(query).to_dataframe()

def execute_engine_simulation(payload):
    if "calls" in payload:
        json_entry = payload["calls"][0][0]
    else:
        json_entry = payload
        
    json_str = json.dumps(json_entry).replace("'", "\\'")
    
    sql = f"""
    SELECT `din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine(
      PARSE_JSON('{json_str}')
    ) as f0_
    """
    
    try:
        query_job = client.query(sql)
        results = query_job.result()
        return [dict(row) for row in results]
    except Exception as e:
        print(f"ERREUR BQ: {e}")
        return []