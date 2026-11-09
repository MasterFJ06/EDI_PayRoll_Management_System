// FastAPI: GET /deductions, GET /tax-rules
import { deductions } from "@/data/mockData";
import { apiClient, mockDelay, USE_MOCKS } from "./api";
import type { Deduction, TaxRule } from "@/types";

const list = <T,>(r: any): T[] => (Array.isArray(r) ? r : r?.items ?? r?.data ?? r?.results ?? []);

export async function listDeductions(): Promise<Deduction[]> {
  return USE_MOCKS ? mockDelay(deductions) : list<Deduction>(await apiClient.get<any>("/deductions"));
}

export async function listTaxRules(): Promise<TaxRule[]> {
  return USE_MOCKS
    ? mockDelay([
        {
          id: "TR01",
          rule_name: "Standard Deduction",
          regime: "New & Old",
          slab_details: "Flat Rs 75,000 deduction on salaried income",
          applicable_year: "FY 2026-27",
          is_active: true,
        },
        {
          id: "TR02",
          rule_name: "Section 80C PF Deduction",
          regime: "Old Regime",
          slab_details: "Up to Rs 1,50,000 per financial year",
          applicable_year: "FY 2026-27",
          is_active: true,
        },
        {
          id: "TR03",
          rule_name: "Professional Tax Exemption",
          regime: "All",
          slab_details: "Deductible under Section 16(iii)",
          applicable_year: "FY 2026-27",
          is_active: true,
        },
      ])
    : list<TaxRule>(await apiClient.get<any>("/tax-rules"));
}
