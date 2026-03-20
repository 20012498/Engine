import streamlit as st
from google.cloud import bigquery
import pandas as pd
import json

PROJECT_ID = "din-homeindex-dev-irq"
client = bigquery.Client(project=PROJECT_ID, location="EU")

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
            'criteriaValue', criteriaValue,
            'criteriaValueIdentifier', criteriaValueIdentifier,
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
        WHERE JSON_VALUE(pillar, '$.pillarCode') = 'DUR'
    ),
    catalogue AS (
        SELECT prod.*, art.itemPicture, art.itemName
        FROM `dfdp-data-foundation-prod.productDataFoundation.productCatalogue` prod
        INNER JOIN `din-homeindex-prd-08n.homeIndexPerformance.article` art
          ON art.businessUnitIdentifier = prod.businessUnitIdentifier
          AND art.itemIdentifier = prod.productBuReference
        WHERE prod.businessUnitIdentifier = {bu_id} AND prod.productBuReference = {prod_ref}
    )
    SELECT c.*, s.criteriaCode, s.criteriaNote, e.productDescriptiveModelIdentifier, e.supplierPurchaseSiteIdentifier
    FROM catalogue c
    LEFT JOIN scores s ON 1=1
    LEFT JOIN (SELECT DISTINCT productDescriptiveModelIdentifier, supplierPurchaseSiteIdentifier FROM engine_call) e ON 1=1
    """
    return client.query(query).to_dataframe()

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

def get_criteria_details(bu_id, prod_ref, top_intl, criteria_code):
    query = f"""
    SELECT 
        m.characteristicIdentifier as att_id, 
        m.methodName, 
        p.characteristicName as att_name,  -- <--- VÉRIFIE BIEN CETTE LIGNE
        p.value as current_value, 
        p.valueIdentifier as val_id
    FROM `din-homeindex-dev-irq.homeIndex.homeIndexCharacteristic` m
    LEFT JOIN `dfdp-data-foundation-prod.productDataFoundation.productCharacteristicsDenormalized` p
        ON p.characteristicIdentifier = m.characteristicIdentifier
        AND p.productBuReference = {prod_ref} AND p.businessUnitIdentifier = {bu_id}
    WHERE m.methodIdentifier = '{criteria_code}'
    LIMIT 1
    """
    return client.query(query).to_dataframe()

def execute_engine_simulation(payload):
    # Sécurisation des quotes pour le SQL
    payload_str = json.dumps(payload).replace("'", "\\'")
    query = f"""
    SELECT TO_JSON_STRING(`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine(PARSE_JSON('{payload_str}'))) as res
    """
    df = client.query(query).to_dataframe()
    if not df.empty and df['res'].iloc[0]:
        return json.loads(df['res'].iloc[0])
    return None