/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_2630615650")

  // update collection data
  unmarshal({
    "listRule": "@request.auth.role = \"super_admin\" || @request.auth.role = \"service\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = id)",
    "viewRule": "@request.auth.role = \"super_admin\" || @request.auth.role = \"service\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = id)"
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_2630615650")

  // update collection data
  unmarshal({
    "listRule": "@request.auth.id != \"\"",
    "viewRule": "@request.auth.id != \"\""
  }, collection)

  return app.save(collection)
})
