/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("_pb_users_auth_")

  // update collection data
  unmarshal({
    "createRule": "(@request.auth.role = \"service\" && @request.body.role = \"user\") || @request.auth.role = \"super_admin\"",
    "updateRule": "(id = @request.auth.id && @request.body.role:isset = false) || @request.auth.role = \"super_admin\""
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("_pb_users_auth_")

  // update collection data
  unmarshal({
    "createRule": "@request.auth.role = \"service\" || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)",
    "updateRule": "(id = @request.auth.id && @request.body.role:isset = false) || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)"
  }, collection)

  return app.save(collection)
})
