import { test } from "node:test";
import assert from "node:assert/strict";
import { inBbox, applyFilters, byDistance, matchPlace } from "../web/src/lib/filters.js";

const L = [
  { id:"a", lng:77.60, lat:12.90, rent:30000, bhk:"2 BHK", listing_type:"entire_flat", furnishing:"Fully furnished", location:"HSR Layout Sector 2" },
  { id:"b", lng:77.64, lat:12.93, rent:16000, bhk:"1 BHK", listing_type:"flatmate", furnishing:"semi_furnished", location:"Koramangala 8th Block" },
  { id:"c", lng:77.70, lat:12.95, rent:45000, bhk:"3 BHK", listing_type:"pg_hostel", furnishing:null, location:"Indiranagar" },
];
test("inBbox", () => assert.deepEqual(L.filter(x=>inBbox(x,[77.59,12.89,77.66,12.94])).map(x=>x.id), ["a","b"]));
test("rent range", () => assert.deepEqual(applyFilters(L,{rentMin:20000,rentMax:40000}).map(x=>x.id), ["a"]));
test("bhk+type", () => { assert.deepEqual(applyFilters(L,{bhk:["1","2"]}).map(x=>x.id), ["a","b"]);
  assert.deepEqual(applyFilters(L,{type:["pg_hostel"]}).map(x=>x.id), ["c"]); });
test("furnishing", () => { assert.deepEqual(applyFilters(L,{furnishing:["furnished"]}).map(x=>x.id), ["a"]);
  assert.deepEqual(applyFilters(L,{furnishing:["semi"]}).map(x=>x.id), ["b"]); });
test("byDistance", () => assert.deepEqual(byDistance(L,[77.60,12.90]).map(x=>x.id), ["a","b","c"]));
test("matchPlace", () => assert.equal(matchPlace("koramangala", L).id, "b"));
