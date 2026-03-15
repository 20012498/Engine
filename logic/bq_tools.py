import streamlit as st
from google.cloud import bigquery
import pandas as pd

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
    bu_proof = 15 if top_intl == 1 else bu_id
    query = f"""
    SELECT 
        m.characteristicIdentifier as att_id, m.methodName, p.characteristicName as att_name,
        p.value as current_value, p.valueIdentifier as val_id,
        proof.productDocumentaryProofName as proof_name,
        CAST(proof.productDocumentaryInterventionIsDone AS BOOL) as is_done
    FROM `din-homeindex-dev-irq.homeIndex.homeIndexCharacteristic` m
    LEFT JOIN `dfdp-data-foundation-prod.productDataFoundation.productCharacteristicsDenormalized` p
        ON p.characteristicIdentifier = m.characteristicIdentifier
        AND p.productBuReference = {prod_ref} AND p.businessUnitIdentifier = {bu_id}
    LEFT JOIN `dfdp-data-foundation-prod.productDataFoundation.productDocumentaryProof` proof
        ON p.productBuReference = proof.productBuReference 
        AND p.characteristicIdentifier = proof.productDocumentaryProofClaimedBy
        AND proof.businessUnitIdentifier = {bu_proof}
    WHERE m.methodIdentifier = '{criteria_code}'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY p.characteristicIdentifier ORDER BY proof.productDocumentaryProofIsActive DESC, proof.productDocumentaryInterventionIsDone DESC) = 1
    """
    return client.query(query).to_dataframe()

def get_simulated_score(bu_id, prod_ref, model_id, supplier_id, current_choices):
    criteria_rows = []
    for c in current_choices:
        v_id = c.get('val_id', '')
        if c['code'] == 'SPPA': v_id = ""
        row = f"JSON_OBJECT('criteriaCode', '{c['code']}', 'criteriaValue', '{c['val']}', 'criteriaValueIdentifier', '{v_id}', 'proof', '{c.get('proof', 'Yes')}', 'characteristic', '{c.get('att_id', '')}')"
        criteria_rows.append(row)
    
    query = f"""
    WITH simu_input AS (
      SELECT TO_JSON_STRING(JSON_STRIP_NULLS(JSON_OBJECT(
        'productBuReference', {prod_ref}, 'businessUnitIdentifier', {bu_id}, 
        'productDescriptiveModelIdentifier', '{model_id}', 'supplierPurchaseSiteIdentifier', '{supplier_id}',
        'criteria', ARRAY[{",".join(criteria_rows)}]
      ))) AS json_entry
    ),
    simu_output AS (
      SELECT TO_JSON_STRING(`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine(PARSE_JSON(json_entry))) AS result_json
      FROM simu_input
    )
    SELECT JSON_VALUE(criterion, '$.criteriaCode') AS criteriaCode, SAFE_CAST(JSON_VALUE(criterion, '$.criteriaNote') AS FLOAT64) AS criteria_note
    FROM simu_output, UNNEST(JSON_QUERY_ARRAY(result_json, '$[0].pillars')) AS pillar, UNNEST(JSON_QUERY_ARRAY(pillar, '$.criteria')) AS criterion
    WHERE JSON_VALUE(pillar, '$.pillarCode') = 'DUR'
    """
    return client.query(query).to_dataframe()